from typing import TypedDict, Optional, List

class InterviewState(TypedDict):
    # Phase control
    phase: str
    # Candidate info
    candidate_info: dict
    # Conversation history
    messages: list
    # Technical phase
    questions: list
    question_index: int
    scores: list
    weak_topics: list
    awaiting_followup: bool
    followup_count: int
    # BUG 4 FIX: hold score during follow-up, commit only when question is resolved
    pending_score: Optional[int]
    # I/O between graph and agent
    last_user_input: str
    last_response: str
    # Persistence
    result_saved: Optional[bool]
    saved_result_id: Optional[str]
    # ── Rich interview context (for role-aware, JD-aware, resume-aware Q&A) ──
    job_description: str
    candidate_skills: List[str]
    resume_summary: str
    github_data: dict
    experience_level: str         # "junior" | "mid" | "senior" | "lead"
    question_category: str        # current question category label
    difficulty_level: str         # "basic" | "intermediate" | "advanced" | "expert"
    interview_round: int          # round number for adaptive context
    role: str                     # normalised role label (frontend/backend/etc.)
