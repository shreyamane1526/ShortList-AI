import logging
import json
import re
from nodes.utils import get_llm, build_messages, strip_tag, load_questions_for_trade
from state import InterviewState
from database import save_result

logger = logging.getLogger("skillfit.technical")

TECHNICAL_CONVERSATION_PROMPT = """You are Priya, a warm and patient technical interviewer for AI SkillFit.
You are conducting a VOICE interview. The candidate is SPEAKING to you.

You just asked the candidate a technical question. Now you are processing their response.

IMPORTANT RULES:
- If the candidate says "repeat", "what?", "sorry?", "can you say that again",
  "I didn't understand", "one more time", or ANYTHING that suggests they want the
  question repeated — you MUST repeat the original question in a friendly way.
  Set action to "repeat".
- If the candidate says "I don't know", "not sure", "no idea", or gives a clearly
  empty/non-answer — acknowledge it kindly ("No worries, that's perfectly fine.")
  and set action to "skip".
- If the candidate gives an actual answer (even partial) — set action to "answered".
- If the candidate asks for clarification or seems confused — rephrase the question
  more simply. Set action to "repeat".

Respond ONLY with a JSON object:
{
  "action": "repeat" | "skip" | "answered",
  "spoken_response": "what Priya should say (empty string if action is answered)"
}

No markdown. Just JSON."""


def load_questions_node(state: InterviewState) -> InterviewState:
    trade = state["candidate_info"].get("trade", "")

    # Gather rich context from state for role-aware question generation
    job_description = state.get("job_description", "")
    candidate_skills = state.get("candidate_skills", [])
    resume_summary = state.get("resume_summary", "")
    github_data = state.get("github_data", {})
    experience_level = state.get("experience_level", "mid")
    # Pass previous answers and scores for adaptive difficulty + continuity
    previous_answers = state.get("messages", [])
    evaluation_scores = state.get("scores", [])

    questions = load_questions_for_trade(
        trade=trade,
        job_description=job_description,
        candidate_skills=candidate_skills,
        resume_summary=resume_summary,
        github_data=github_data,
        experience_level=experience_level,
        previous_answers=previous_answers,
        evaluation_scores=evaluation_scores,
    )

    if not questions:
        logger.warning(f"[Technical] No questions found for trade: {trade}")

    logger.info(f"[Technical] Loaded {len(questions)} questions for {trade}")

    return {
        **state,
        "questions": questions,
        "question_index": 0,
        "scores": [],
        "weak_topics": [],
        "awaiting_followup": False,
        "followup_count": 0,
        "pending_score": None,
        "messages": [],
        "phase": "technical_ask",
    }


def _determine_difficulty(scores: list) -> str:
    """Adapt difficulty based on recent performance."""
    if not scores:
        return "intermediate"
    recent = scores[-3:] if len(scores) >= 3 else scores
    avg = sum(recent) / len(recent)
    if avg >= 8.0:
        return "expert"
    elif avg >= 6.5:
        return "advanced"
    elif avg >= 4.5:
        return "intermediate"
    return "basic"


def technical_ask_node(state: InterviewState) -> InterviewState:
    """Asks the current question naturally with a warm transition and adaptive context."""
    questions = state["questions"]
    index = state["question_index"]

    if index >= len(questions):
        return {**state, "phase": "close"}

    current_q = questions[index]
    candidate_name = state["candidate_info"].get("name", "")
    total = len(questions)

    # ── Adaptive difficulty ──
    difficulty = _determine_difficulty(state.get("scores", []))
    question_difficulty = current_q.get("difficulty", difficulty)

    # ── Store metadata in state for frontend ──
    state["question_category"] = current_q.get("topic", "Technical")
    state["difficulty_level"] = question_difficulty

    llm = get_llm(temperature=0.6, max_tokens=120)

    # ── Conversational continuity: reference previous answer if available ──
    prev_reference = ""
    prev_messages = state.get("messages", [])
    if index > 0 and prev_messages:
        last_user_msgs = [m for m in prev_messages if m.get("role") == "user"]
        if last_user_msgs:
            last_answer = last_user_msgs[-1].get("content", "")[:80]
            prev_reference = f"The candidate's last answer was about: \"{last_answer}\". Reference this naturally if relevant to transition."

    if index == 0:
        context = f"This is the FIRST technical question. Warmly transition into the technical round. Address the candidate by name ({candidate_name}) and let them know you'll ask some questions about their trade. Then ask the question. {prev_reference}"
    elif index == total - 1:
        context = f"This is the LAST question. Mention warmly that this is the final one before asking. {prev_reference}"
    else:
        context = f"Transition naturally from the previous question/answer. Use a brief acknowledgment like 'Alright' or 'Okay, moving on' — keep it short and warm. {prev_reference}"

    transition_prompt = f"""You are Priya, a warm professional interviewer conducting a voice interview.

{context}

Generate a natural spoken response that transitions into this question.
Include the question at the end of your response.
Keep the total response under 40 words.
No bullet points, no markdown. Speak naturally.

Difficulty level of this question: {question_difficulty}
Question to ask: "{current_q['question']}" """

    response = llm.invoke(transition_prompt).content.strip()

    logger.info(f"[Technical] Asking Q{index + 1}/{total} ({question_difficulty}): {current_q['question'][:60]}")

    return {
        **state,
        "last_response": response,
        "messages": [
            {"role": "assistant", "content": response},
        ],
        "phase": "technical_listen",
    }


def technical_score_node(state: InterviewState) -> InterviewState:
    """Processes the candidate's answer — handles repeats, scores, and decides next step."""
    questions = state["questions"]
    index = state["question_index"]
    current_q = questions[index]
    user_answer = state["last_user_input"]
    candidate_info = state["candidate_info"]

    # ── Step 1: Check if the candidate wants a repeat or gave a non-answer ──
    conversation_llm = get_llm(temperature=0.2, max_tokens=200)

    classify_prompt = f"""{TECHNICAL_CONVERSATION_PROMPT}

Original question asked: {current_q['question']}
Candidate's response: "{user_answer}"
"""

    classify_result = conversation_llm.invoke(classify_prompt)
    try:
        clean = re.sub(r"```json|```", "", classify_result.content).strip()
        classify_data = json.loads(clean)
    except Exception:
        classify_data = {"action": "answered", "spoken_response": ""}

    action = classify_data.get("action", "answered")
    spoken = classify_data.get("spoken_response", "")

    logger.info(f"[Technical] Q{index + 1} action: {action}")

    # ── Handle repeat request ──
    if action == "repeat":
        logger.info(f"[Technical] Candidate asked to repeat Q{index + 1}")
        return {
            **state,
            "last_response": spoken if spoken else f"Of course! {current_q['question']}",
            "phase": "technical_listen",  # stay on same question, wait for answer
        }

    # ── Handle skip / "I don't know" ──
    if action == "skip":
        scores = state["scores"] + [0]
        weak_topics = state["weak_topics"] + [current_q["topic"]]
        next_index = index + 1
        phase = "close" if next_index >= len(questions) else "technical_ask"

        # Generate a warm acknowledgment
        skip_response = spoken if spoken else "No worries at all, that's perfectly fine. Let's move to the next one."

        logger.info(f"[Technical] Candidate skipped Q{index + 1}, scored 0")

        return {
            **state,
            "scores": scores,
            "weak_topics": weak_topics,
            "question_index": next_index,
            "awaiting_followup": False,
            "followup_count": 0,
            "last_response": skip_response,
            "phase": phase,
        }

    # ── Step 2: Score the actual answer ──
    score_llm = get_llm(temperature=0, max_tokens=500)

    q_conversation = state.get("messages", [])
    q_history = "\n".join(f"{m['role']}: {m['content']}" for m in q_conversation)

    # Gather rich context for enhanced scoring
    job_description = state.get("job_description", "")
    candidate_skills = state.get("candidate_skills", [])
    resume_summary = state.get("resume_summary", "")
    skills_str = ", ".join(candidate_skills[:10]) if candidate_skills else "not specified"
    difficulty = _determine_difficulty(state.get("scores", []))

    score_prompt = f"""You are an expert senior technical assessor at a top-tier tech company (FAANG-level), conducting an in-depth software engineering interview.

CONTEXT:
- Role/Trade: {candidate_info.get('trade')}
- Experience: {candidate_info.get('years_of_experience')} years
- Candidate Skills: {skills_str}
- Topic: {current_q.get('topic', 'Technical')}
- Current Difficulty: {difficulty}
- Question: {current_q.get('question', '')}
- Ideal answer key points: {current_q.get('ideal_answer', '')}

JOB DESCRIPTION CONTEXT:
{job_description[:400] if job_description else 'Not provided'}

CANDIDATE'S RESUME/BACKGROUND:
{resume_summary[:300] if resume_summary else 'Not provided'}

CONVERSATION FOR THIS QUESTION:
{q_history}
user: {user_answer}

SCORING GUIDELINES:
- This is a spoken interview. Candidates may use informal language and explain things in their own words.
- Score based on PRACTICAL UNDERSTANDING and technical accuracy, not textbook-perfect wording.
- If the candidate demonstrates understanding through examples or real-world experience, give credit.
- For software roles: assess technical depth, system thinking, and awareness of trade-offs.
- 9-10: Exceptional — deep expertise, mentions trade-offs, gives concrete examples, system-level thinking
- 7-8: Strong — covers key concepts correctly, some depth, minor gaps
- 5-6: Adequate — understands basics but lacks depth, missing important nuances
- 3-4: Weak — partial understanding, significant gaps or misconceptions
- 0-2: Very weak — incorrect, off-topic, or no meaningful answer
- Consider experience level: {candidate_info.get('years_of_experience')} years. Expect more depth from senior candidates.
- A score of 4-7 with specific gaps SHOULD trigger a follow-up to give the candidate a fair chance.
- Be FAIR but RIGOROUS. Vague buzzword-dropping without substance scores 3-4.

DIMENSION SCORES (each 1-10):
- technical_depth: How technically accurate and deep is the answer?
- clarity: How clearly is the answer communicated?
- relevance: How relevant is the answer to the question asked?
- communication: Is the answer well-structured and easy to follow?

IMPORTANT: Do NOT ask about or score answers related to HVAC, plumbing, construction, woodworking,
or any non-software vocational topic. If the question is about software engineering, score it as such.

Return ONLY a JSON object:
{{
  "score": <integer 0-10>,
  "technical_depth": <integer 1-10>,
  "clarity": <integer 1-10>,
  "relevance": <integer 1-10>,
  "communication": <integer 1-10>,
  "needs_followup": <true if score is 4-7 and there are specific gaps to probe>,
  "gap": "<one sentence describing what key point was missing, empty if score >= 8>",
  "strength": "<one sentence on what the candidate got right, empty if score <= 2>",
  "is_weak": <true only if score <= 3 and the answer shows no understanding at all>,
  "interviewer_observation": "<one sentence observation about the candidate's thinking process or approach>"
}}

No markdown. Just JSON."""

    result = score_llm.invoke(score_prompt)
    try:
        clean = re.sub(r"```json|```", "", result.content).strip()
        score_data = json.loads(clean)
    except Exception:
        score_data = {"score": 5, "needs_followup": True, "gap": "", "strength": "", "is_weak": False, "technical_depth": 5, "clarity": 5, "relevance": 5, "communication": 5, "interviewer_observation": ""}

    score = score_data.get("score", 5)
    needs_followup = score_data.get("needs_followup", False)
    gap = score_data.get("gap", "")
    strength = score_data.get("strength", "")
    is_weak = score_data.get("is_weak", False)

    # Enhanced dimension scores for richer feedback
    technical_depth = score_data.get("technical_depth", score)
    clarity = score_data.get("clarity", score)
    relevance = score_data.get("relevance", score)
    communication = score_data.get("communication", score)
    interviewer_observation = score_data.get("interviewer_observation", "")

    followup_count = state["followup_count"]

    logger.info(
        f"[Score] Q{index + 1}: {score}/10 | "
        f"Followup: {needs_followup} | Weak: {is_weak} | "
        f"Strength: {strength[:50]} | Gap: {gap[:50]}"
    )

    # ── Decision logic ──

    # BUG 4 FIX: When committing a final score, take the max of the new score
    # and any pending_score held from a previous follow-up round.
    pending_score = state.get("pending_score")

    def _commit_score(final_score: int, is_weak_topic: bool = False) -> dict:
        """Commit the best score seen for this question and advance."""
        committed = max(final_score, pending_score or 0)
        scores = state["scores"] + [committed]
        next_index = index + 1
        phase = "close" if next_index >= len(questions) else "technical_ask"
        update = {
            **state,
            "scores": scores,
            "pending_score": None,
            "question_index": next_index,
            "awaiting_followup": False,
            "followup_count": 0,
            "phase": phase,
        }
        if is_weak_topic:
            update["weak_topics"] = state["weak_topics"] + [current_q["topic"]]
        return update

    # Good answer (8+) or no followup needed — acknowledge and move on
    if score >= 8 or (not needs_followup and not is_weak):
        return _commit_score(score)

    # Weak answer with no hope of recovery — be kind and move on
    if is_weak or followup_count >= 2:
        return _commit_score(score, is_weak_topic=True)

    # ── Generate a meaningful follow-up ──
    followup_llm = get_llm(temperature=0.5, max_tokens=150)

    # Build conversational context from previous answers if available
    prev_context = ""
    all_messages = state.get("messages", [])
    prev_user_answers = [m for m in all_messages if m.get("role") == "user"]
    if len(prev_user_answers) > 1:
        # Reference something from a prior answer for continuity
        prior = prev_user_answers[-2].get("content", "")[:60]
        prev_context = f"The candidate previously mentioned: \"{prior}\". If relevant, connect this follow-up to that context."

    followup_prompt = f"""You are Priya, a warm and encouraging senior technical interviewer at a top-tier tech company.
The candidate answered a question about {current_q.get('topic', 'this topic')}.

What they got right: {strength}
What was missing: {gap}
Original question: {current_q.get('question', '')}
Their answer: {user_answer}
{prev_context}

Generate a warm, conversational follow-up that:
1. First ACKNOWLEDGES what they got right (briefly, 1 sentence).
2. Then asks a specific follow-up question to probe the gap area.
3. The follow-up should feel like a natural continuation of a real FAANG interview, not a test.
4. Keep total response under 30 words.
5. Do NOT repeat the original question. Ask something specific about the gap.
6. Sound like a senior engineer probing deeper, not a teacher testing.

Example good follow-ups:
- "You mentioned caching — how did you handle cache invalidation consistency?"
- "Good point on the indexing. What about write-performance trade-offs with that approach?"
- "I see you've used React hooks — have you run into any stale closure issues?"

Just the spoken response, nothing else."""

    followup_q = followup_llm.invoke(followup_prompt).content.strip()

    # Update per-question conversation with the answer and follow-up
    updated_messages = state.get("messages", []) + [
        {"role": "user", "content": user_answer},
        {"role": "assistant", "content": followup_q},
    ]

    logger.info(f"[Technical] Follow-up #{followup_count + 1} for Q{index + 1}: {followup_q[:60]}")

    # BUG 4 FIX: Store score as pending — do NOT append to scores yet.
    # The score will be committed (or superseded) when the follow-up answer arrives.
    return {
        **state,
        "pending_score": score,          # hold, don't commit yet
        "awaiting_followup": True,
        "followup_count": followup_count + 1,
        "last_response": followup_q,
        "messages": updated_messages,
        "phase": "technical_listen",
    }


def _generate_feedback(
    scores: list,
    weak_topics: list,
    questions: list,
    candidate_info: dict,
    avg: float,
) -> dict:
    """
    Generates structured feedback: strengths, improvements, interviewer observations,
    and follow-up recommendations.
    Uses scored questions to identify strong and weak areas.
    """
    feedback_llm = get_llm(temperature=0.3, max_tokens=600)

    # Build a summary of per-topic performance
    topic_scores: dict[str, list] = {}
    for i, q in enumerate(questions):
        topic = q.get("topic", "General")
        if i < len(scores):
            topic_scores.setdefault(topic, []).append(scores[i])

    topic_avg = {t: round(sum(s) / len(s), 1) for t, s in topic_scores.items()}
    strong_topics = [t for t, a in topic_avg.items() if a >= 7.0]
    improvement_topics = weak_topics or [t for t, a in topic_avg.items() if a < 5.0]

    trade = candidate_info.get("trade", "Software Engineer")
    is_software = any(kw in trade.lower() for kw in (
        "engineer", "developer", "programmer", "software", "frontend", "backend",
    ))

    # Build per-question detail for richer feedback
    q_details = []
    for i, q in enumerate(questions[:10]):
        if i < len(scores):
            q_details.append(f"- {q.get('topic', 'General')}: scored {scores[i]}/10")

    q_detail_str = "\n".join(q_details)

    domain_context = "software engineering" if is_software else "technical"

    feedback_prompt = f"""You are an expert senior {domain_context} assessor reviewing a technical interview for {trade}.

Candidate: {candidate_info.get('name', '')}
Role: {candidate_info.get('trade', '')}
Experience: {candidate_info.get('years_of_experience', '')} years
Average score: {avg}/10

PER-QUESTION BREAKDOWN:
{q_detail_str}

Strong topics: {', '.join(strong_topics) if strong_topics else 'None identified'}
Topics needing improvement: {', '.join(improvement_topics) if improvement_topics else 'None'}

Generate a JSON object with exactly this structure:
{{
  "strengths": ["<specific strength observation 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<constructive improvement 1>", "<improvement 2>"],
  "interviewer_observations": ["<observation 1 about thinking/approach>", "<observation 2>"],
  "follow_up_recommendations": ["<what to review next>", "<recommendation 2>"]
}}

Rules:
- Strengths should be specific technical observations (e.g. "Strong understanding of React reconciliation")
- Improvements should be constructive and actionable (e.g. "Review database indexing strategies for large-scale queries")
- If no strong topics, base strengths on communication or problem-solving approach
- Interviewer observations should note how the candidate thinks and approaches problems
- Follow-up recommendations should suggest specific topics for the candidate to review
- Keep each item under 12 words
- Return ONLY the JSON object, no markdown"""

    try:
        result = feedback_llm.invoke(feedback_prompt)
        clean = re.sub(r"```json|```", "", result.content).strip()
        feedback = json.loads(clean)
        # Validate structure
        if "strengths" not in feedback or "improvements" not in feedback:
            raise ValueError("Missing keys")
        return feedback
    except Exception as e:
        logger.warning(f"[Close] Feedback generation failed: {e}, using defaults")
        return {
            "strengths": [f"Completed the {candidate_info.get('trade', 'trade')} assessment"],
            "improvements": [f"Review {t}" for t in improvement_topics[:2]] or ["Continue practising technical skills"],
            "interviewer_observations": ["Candidate showed willingness to engage with technical topics"],
            "follow_up_recommendations": [f"Deepen understanding of {t}" for t in improvement_topics[:2]] or ["Practice with real-world scenarios"],
        }


def persist_interview_result(state: InterviewState, *, partial: bool = False) -> InterviewState:
    """Persist the current interview state once. Safe to call from close/exit paths."""
    if state.get("result_saved"):
        return state

    scores = state.get("scores", [])
    if not scores:
        logger.warning("[Persist] No scored answers yet; skipping result save.")
        return state

    avg = round(sum(scores) / len(scores), 1)
    weak_topics = list(set(state.get("weak_topics", [])))
    candidate_info = state.get("candidate_info", {})
    questions = state.get("questions", [])

    from database import check_integrity_flag

    if partial:
        fitment = "Requires Manual Verification"
    elif avg >= 7.5:
        fitment = "Job-Ready"
    elif avg >= 5.0:
        fitment = "Requires Training"
    elif avg >= 3.0:
        fitment = "Low Confidence"
    else:
        fitment = "Requires Significant Upskilling"

    if check_integrity_flag(scores, avg):
        fitment = "Requires Manual Verification"

    feedback = _generate_feedback(scores, weak_topics, questions, candidate_info, avg)
    transcript = state.get("messages", [])

    try:
        record_id = save_result(
            candidate_name=candidate_info.get("name", "Unknown"),
            phone_number=candidate_info.get("phone_number", ""),
            trade=candidate_info.get("trade", ""),
            scores=scores,
            weak_topics=weak_topics,
            fitment=fitment,
            average_score=avg,
            language=candidate_info.get("language", "English"),
            district=candidate_info.get("district"),
            feedback=feedback,
            transcript=transcript,
            email=candidate_info.get("email", ""),
            job_id=candidate_info.get("job_id") or None,
            user_id=candidate_info.get("user_id") or None,
            livekit_room=candidate_info.get("livekit_room") or None,
        )
        logger.info(f"[Persist] Results saved — record ID: {record_id}")
        return {**state, "result_saved": True, "saved_result_id": record_id}
    except Exception as e:
        logger.error(f"[Persist] Failed to save results: {e}")
        return state


def close_interview_node(state: InterviewState) -> InterviewState:
    scores = state["scores"]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    weak_topics = list(set(state["weak_topics"]))
    candidate_info = state["candidate_info"]
    questions = state.get("questions", [])

    from database import check_integrity_flag

    if avg >= 7.5:
        fitment = "Job-Ready"
    elif avg >= 5.0:
        fitment = "Requires Training"
    elif avg >= 3.0:
        fitment = "Low Confidence"
    else:
        fitment = "Requires Significant Upskilling"

    # Override with Manual Verification if integrity is suspicious
    if check_integrity_flag(scores, avg):
        fitment = "Requires Manual Verification"

    logger.info(f"[Close] Candidate: {candidate_info} | Avg: {avg} | Fitment: {fitment} | Weak: {weak_topics}")

    state = persist_interview_result(state)

    # ── Generate warm closing message ──
    close_llm = get_llm(temperature=0.7, max_tokens=200)

    weak_str = ""
    if weak_topics:
        weak_str = f"Areas where the candidate could improve: {', '.join(weak_topics)}."

    close_prompt = f"""You are Priya, a warm interviewer closing a voice interview.

Candidate name: {candidate_info.get('name', '')}
Trade: {candidate_info.get('trade', '')}
Average score: {avg}/10
{weak_str}

Generate a warm, encouraging closing statement. Rules:
- Thank the candidate by name for their time.
- If there are weak areas, mention them gently as "areas to keep learning about" — 
  never say "you were weak in" or anything discouraging.
- End on a positive, encouraging note.
- Keep it under 4 sentences.
- Speak naturally, no bullet points or lists.

Just the spoken response."""

    closing = close_llm.invoke(close_prompt).content.strip()

    return {
        **state,
        "last_response": closing,
        "phase": "done",
    }
