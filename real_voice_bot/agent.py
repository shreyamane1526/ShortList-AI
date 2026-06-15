import logging
import asyncio
import os
import re
import json
import time
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import sarvam

from nodes.icebreaker import icebreaker_node, extract_info_node
from nodes.experience import experience_node
from nodes.technical import (
    load_questions_node,
    technical_ask_node,
    technical_score_node,
    close_interview_node,
    persist_interview_result,
)
from nodes.utils import get_llm
from state import InterviewState

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skillfit-voice")

LANGUAGE_OPTIONS = {
    "english": ("en-IN", "English"),
    "hindi": ("hi-IN", "Hindi"),
    "bengali": ("bn-IN", "Bengali"),
    "bangla": ("bn-IN", "Bengali"),
    "tamil": ("ta-IN", "Tamil"),
    "telugu": ("te-IN", "Telugu"),
    "gujarati": ("gu-IN", "Gujarati"),
    "kannada": ("kn-IN", "Kannada"),
    "malayalam": ("ml-IN", "Malayalam"),
    "marathi": ("mr-IN", "Marathi"),
    "punjabi": ("pa-IN", "Punjabi"),
    "odia": ("od-IN", "Odia"),
    "oriya": ("od-IN", "Odia"),
}


# IMPROVEMENT 1: Better language detection — matches language name anywhere in utterance
def detect_language_preference(user_text: str) -> tuple[str, str] | None:
    normalized = user_text.lower().strip()
    for language, config in LANGUAGE_OPTIONS.items():
        if re.search(rf'\b{re.escape(language)}\b', normalized):
            return config
    return None


def translate_for_tts(text: str, language_name: str) -> str:
    if language_name == "English":
        return text

    llm = get_llm(temperature=0, max_tokens=250)
    prompt = f"""Translate this spoken interview response into {language_name}.
Keep it natural, respectful, and conversational.
Return only the translated sentence or sentences.
No markdown, no explanation.

Text:
{text}"""
    return llm.invoke(prompt).content.strip()


def get_initial_state() -> InterviewState:
    return {
        "phase": "icebreaker",
        "candidate_info": {},
        "messages": [],
        "questions": [],
        "question_index": 0,
        "scores": [],
        "weak_topics": [],
        "awaiting_followup": False,
        "followup_count": 0,
        "pending_score": None,
        "last_user_input": "",
        "last_response": "",
        "result_saved": False,
        "saved_result_id": None,
        "job_description": "",
        "candidate_skills": [],
        "resume_summary": "",
        "github_data": {},
        "experience_level": "mid",
        "question_category": "",
        "difficulty_level": "intermediate",
        "interview_round": 1,
        "role": "software_general",
    }


def run_interview_step(state: InterviewState) -> InterviewState:
    """
    Simple phase-based dispatcher.
    Runs the correct node(s) based on state['phase'] and chains
    transitions until the graph needs to pause for user input.
    """
    MAX_STEPS = 15  # safety limit to prevent infinite loops

    for _ in range(MAX_STEPS):
        phase = state["phase"]
        logger.info(f"[Dispatcher] Phase: {phase}")

        if phase == "icebreaker":
            state = icebreaker_node(state)
            if state["phase"] == "extract_info":
                continue
            return state

        elif phase == "extract_info":
            state = extract_info_node(state)
            continue

        elif phase == "experience":
            state = experience_node(state)
            if state["phase"] == "load_questions":
                continue
            return state

        elif phase == "load_questions":
            state = load_questions_node(state)
            continue

        elif phase == "technical_ask":
            state = technical_ask_node(state)
            # BUG 2 FIX: After asking, immediately score (the question was just asked,
            # but we need to wait for user input — technical_ask sets phase="technical_listen")
            return state

        elif phase == "technical_listen":
            # BUG 2 FIX: We have the user's answer in last_user_input — score it now
            state = technical_score_node(state)
            phase_after = state["phase"]
            if phase_after == "technical_listen":
                # Follow-up was asked — return and wait for next user input
                return state
            # Otherwise continue the loop (go to technical_ask or close)
            continue

        elif phase == "close":
            state = close_interview_node(state)
            return state

        elif phase == "done":
            return state

        else:
            logger.error(f"[Dispatcher] Unknown phase: {phase}")
            return state

    logger.error("[Dispatcher] Hit max steps — breaking out")
    return state


TRANSCRIPT_TOPIC = "interview-transcript"
SCORES_TOPIC = "interview-scores"


class VoiceAgent(Agent):
    def __init__(self, room: rtc.Room, initial_candidate_info: dict | None = None, initial_state_extras: dict | None = None):
        super().__init__(
            instructions="You are Priya, a warm interviewer for AI SkillFit.",
            stt=sarvam.STT(
                language="unknown",
                model="saaras:v3",
                mode="translate",
                flush_signal=True,
            ),
            llm=None,
            tts=sarvam.TTS(
                target_language_code="en-IN",
                model="bulbul:v2",
                speaker="anushka",
            ),
        )
        self.state = get_initial_state()
        # Pre-populate candidate_info from room metadata (phone_number, trade, etc.)
        if initial_candidate_info:
            self.state["candidate_info"].update(initial_candidate_info)
        # Pre-populate rich context fields for role-aware interviewing
        if initial_state_extras:
            for k, v in initial_state_extras.items():
                if k in self.state:
                    self.state[k] = v
        self.language_selected = False
        self.preferred_language_code = "en-IN"
        self.preferred_language_name = "English"
        self.room = room
        # BUG 6 FIX: Lock to prevent concurrent state mutations
        self._processing = asyncio.Lock()
        # IMPROVEMENT 3: Track whether we've initialized the phase after language selection
        self._phase_initialized = False

    async def publish_transcript(self, speaker: str, text: str):
        if not text or not text.strip():
            return

        payload = json.dumps(
            {
                "id": f"{speaker}-{int(time.time() * 1000)}",
                "speaker": speaker,
                "text": text.strip(),
                "timestamp": int(time.time() * 1000),
            },
            ensure_ascii=False,
        ).encode("utf-8")

        try:
            await self.room.local_participant.publish_data(
                payload,
                reliable=True,
                topic=TRANSCRIPT_TOPIC,
            )
        except Exception as exc:
            logger.warning(f"[Transcript] Failed to publish transcript event: {exc}")

    async def publish_scores(self):
        """IMPROVEMENT 4: Publish live score update after each technical question."""
        scores = self.state.get("scores", [])
        if not scores:
            return
        payload = json.dumps({
            "event": "score_update",
            "question_index": self.state.get("question_index", 0),
            "scores": scores,
            "avg": round(sum(scores) / len(scores), 1),
        }).encode("utf-8")
        try:
            await self.room.local_participant.publish_data(
                payload,
                reliable=True,
                topic=SCORES_TOPIC,
            )
        except Exception as exc:
            logger.warning(f"[Scores] Failed to publish score update: {exc}")

    def set_tts_language(self, language_code: str, language_name: str):
        self.preferred_language_code = language_code
        self.preferred_language_name = language_name
        self._tts.update_options(target_language_code=language_code)
        logger.info(f"[Language] TTS set to {language_name} ({language_code})")

    async def say_in_preferred_language(self, text: str):
        spoken_text = translate_for_tts(text, self.preferred_language_name)
        await self.publish_transcript("assistant", spoken_text)
        await self.session.say(spoken_text)

    async def on_enter(self):
        greeting = (
            "Hello! Welcome to AI SkillFit. I'm Priya, your interviewer today. "
            "Which language would you prefer for this interview? You can say English, Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, Gujarati, Malayalam, Punjabi, or Odia."
        )
        await self.publish_transcript("assistant", greeting)
        await self.session.say(greeting)

    async def on_exit(self):
        # IMPROVEMENT 5: Robust partial save on disconnect
        if self.state.get("result_saved"):
            return
        if self.state.get("scores") or self.state.get("phase") not in ("icebreaker", "extract_info"):
            logger.info("[Agent exit] Saving partial result.")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda s=self.state: persist_interview_result(s, partial=True),
            )

    async def on_user_turn_completed(self, turn_ctx, new_message):
        user_text = new_message.text_content
        if not user_text or not user_text.strip():
            return

        await self.publish_transcript("user", user_text)

        if not self.language_selected:
            language = detect_language_preference(user_text)
            if not language:
                retry = (
                    "Sorry, I could not clearly understand the language. "
                    "Please say one language, for example Hindi, Kannada, Tamil, or English."
                )
                await self.publish_transcript("assistant", retry)
                await self.session.say(retry)
                return

            language_code, language_name = language
            self.set_tts_language(language_code, language_name)
            self.language_selected = True

            # Store language in candidate_info so it gets saved with results
            self.state["candidate_info"]["language"] = language_name

            # IMPROVEMENT 3: Skip icebreaker if metadata already has name + trade + experience
            if not self._phase_initialized:
                self._phase_initialized = True
                info = self.state["candidate_info"]
                if info.get("name") and info.get("trade") and info.get("years_of_experience"):
                    self.state["phase"] = "experience"
                    greeting = (
                        f"Great, we'll continue in {language_name}. "
                        f"Hi {info['name']}! Let's start with a few questions about your experience."
                    )
                    await self.say_in_preferred_language(greeting)
                    return

            greeting = (
                f"Great, we will continue in {language_name}. "
                "Could you please start by telling me your name?"
            )
            self.state["messages"] = [
                {"role": "assistant", "content": greeting}
            ]
            await self.say_in_preferred_language(greeting)
            return

        if self.state.get("phase") == "done":
            return

        logger.info(f"[User | Phase: {self.state['phase']}] {user_text}")

        self.state["last_user_input"] = user_text

        # BUG 6 FIX: Use a lock to prevent concurrent state mutations.
        # Capture state by value in the lambda to avoid reference aliasing.
        async with self._processing:
            loop = asyncio.get_event_loop()
            self.state = await loop.run_in_executor(
                None,
                lambda s=self.state: run_interview_step(s),
            )

        response = self.state.get("last_response", "")
        if response:
            logger.info(f"[Agent speaking] {response[:80]}")
            await self.say_in_preferred_language(response)

        # IMPROVEMENT 4: Publish live scores after each technical scoring step
        if self.state.get("scores"):
            await self.publish_scores()


async def entrypoint(ctx: JobContext):
    # Connect to the LiveKit room — audio only, no video
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    logger.info(f"Room connected: {ctx.room.name}")

    # Parse room metadata to pre-populate candidate info
    initial_candidate_info = {}
    initial_state_extras = {}
    try:
        metadata_str = ctx.room.metadata or ""
        if metadata_str:
            metadata = json.loads(metadata_str)
            phone = metadata.get("phone_number", "")
            trade = metadata.get("trade", "")
            email = metadata.get("email", "")
            job_id = metadata.get("job_id", "")
            user_id = metadata.get("user_id", "")
            name = metadata.get("name", "")
            livekit_room = metadata.get("livekit_room", ctx.room.name)
            if user_id:
                initial_candidate_info["user_id"] = user_id
                logger.info(f"[Entrypoint] Pre-populated user_id: {user_id}")
            if phone:
                initial_candidate_info["phone_number"] = phone
                logger.info(f"[Entrypoint] Pre-populated phone_number: {phone}")
            if trade:
                initial_candidate_info["trade"] = trade
                logger.info(f"[Entrypoint] Pre-populated trade: {trade}")
            if email:
                initial_candidate_info["email"] = email
            if job_id:
                initial_candidate_info["job_id"] = job_id
            if name:
                initial_candidate_info["name"] = name
                logger.info(f"[Entrypoint] Pre-populated name: {name}")
            if livekit_room:
                initial_candidate_info["livekit_room"] = livekit_room

            # ── Rich context for role-aware interviewing ──
            if metadata.get("job_description"):
                initial_state_extras["job_description"] = metadata["job_description"]
            if metadata.get("candidate_skills"):
                initial_state_extras["candidate_skills"] = metadata["candidate_skills"]
            if metadata.get("resume_summary"):
                initial_state_extras["resume_summary"] = metadata["resume_summary"]
            if metadata.get("github_data"):
                initial_state_extras["github_data"] = metadata["github_data"]
            if metadata.get("experience_level"):
                initial_state_extras["experience_level"] = metadata["experience_level"]
            if metadata.get("role"):
                initial_state_extras["role"] = metadata["role"]
    except Exception as e:
        logger.warning(f"[Entrypoint] Could not parse room metadata: {e}")

    agent = VoiceAgent(ctx.room, initial_candidate_info=initial_candidate_info, initial_state_extras=initial_state_extras)
    session = AgentSession(min_endpointing_delay=1.5)
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="skillfit-agent"))
