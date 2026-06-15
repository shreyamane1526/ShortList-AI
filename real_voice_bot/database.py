"""
real_voice_bot/database.py

Persistence layer for the LiveKit voice agent.
Saves interview results to the Backend PostgreSQL database via SQLAlchemy,
using the same connection string as the Flask app (DATABASE_URL env var).

Functions expected by technical.py / persist_interview_result:
  - save_result(...)  -> record_id (int)
  - check_integrity_flag(scores, avg) -> bool
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("skillfit.database")

# ── Lazy engine — only created when first needed ──────────────────────────────

_engine = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError(
            "[database] DATABASE_URL is not set. "
            "Add it to real_voice_bot/.env or the environment."
        )

    if db_url.startswith("postgresql"):
        _engine = create_engine(db_url, pool_pre_ping=True)
    else:
        _engine = create_engine(
            db_url, connect_args={"check_same_thread": False}, pool_pre_ping=True
        )
    return _engine


# ── Table definition (mirrors Backend/models.py LiveKitInterview) ─────────────

def _ensure_table():
    """Create livekit_interviews table if it doesn't exist yet."""
    from sqlalchemy import text

    engine = _get_engine()
    create_sql = """
    CREATE TABLE IF NOT EXISTS livekit_interviews (
        id              SERIAL PRIMARY KEY,
        candidate_id    INTEGER,
        evaluation_id   INTEGER,
        livekit_room    VARCHAR(200),
        phone_number    VARCHAR(30),
        trade           VARCHAR(100),
        language        VARCHAR(50)  DEFAULT 'English',
        scores          JSONB        DEFAULT '[]',
        avg_score       FLOAT,
        fitment         VARCHAR(60),
        weak_topics     JSONB        DEFAULT '[]',
        feedback        JSONB,
        transcript      JSONB        DEFAULT '[]',
        status          VARCHAR(20)  DEFAULT 'started',
        started_at      TIMESTAMP    DEFAULT NOW(),
        completed_at    TIMESTAMP
    );
    """
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()


# ── Public API ────────────────────────────────────────────────────────────────

def save_result(
    candidate_name: str,
    phone_number: str,
    trade: str,
    scores: list,
    weak_topics: list,
    fitment: str,
    average_score: float,
    language: str = "English",
    district: Optional[str] = None,
    feedback: Optional[dict] = None,
    transcript: Optional[list] = None,
    email: str = "",
    job_id: Optional[int] = None,
    user_id: Optional[int] = None,
    livekit_room: Optional[str] = None,
    partial: bool = False,
) -> int:
    """
    Upsert an interview result row in livekit_interviews.
    Returns the row id.
    """
    from sqlalchemy import text

    try:
        _ensure_table()
    except Exception as e:
        logger.warning(f"[DB] Could not ensure table: {e}")

    status = "partial" if partial else "completed"
    completed_at = None if partial else datetime.utcnow().isoformat()

    # Resolve candidate_id from user_id if available
    candidate_id: Optional[int] = None
    if user_id:
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id FROM candidates WHERE user_id = :uid LIMIT 1"),
                    {"uid": int(user_id)},
                ).fetchone()
                if row:
                    candidate_id = row[0]
        except Exception as e:
            logger.warning(f"[DB] Could not resolve candidate_id: {e}")

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            # Upsert by livekit_room if available, otherwise insert
            if livekit_room:
                existing = conn.execute(
                    text("SELECT id FROM livekit_interviews WHERE livekit_room = :room LIMIT 1"),
                    {"room": livekit_room},
                ).fetchone()
            else:
                existing = None

            if existing:
                record_id = existing[0]
                conn.execute(
                    text("""
                        UPDATE livekit_interviews SET
                            candidate_id  = :candidate_id,
                            phone_number  = :phone_number,
                            trade         = :trade,
                            language      = :language,
                            scores        = :scores,
                            avg_score     = :avg_score,
                            fitment       = :fitment,
                            weak_topics   = :weak_topics,
                            feedback      = :feedback,
                            transcript    = :transcript,
                            status        = :status,
                            completed_at  = :completed_at
                        WHERE id = :id
                    """),
                    {
                        "candidate_id": candidate_id,
                        "phone_number": phone_number or "",
                        "trade": trade or "",
                        "language": language,
                        "scores": json.dumps(scores),
                        "avg_score": average_score,
                        "fitment": fitment,
                        "weak_topics": json.dumps(weak_topics),
                        "feedback": json.dumps(feedback) if feedback else None,
                        "transcript": json.dumps(transcript or []),
                        "status": status,
                        "completed_at": completed_at,
                        "id": record_id,
                    },
                )
            else:
                result = conn.execute(
                    text("""
                        INSERT INTO livekit_interviews
                            (candidate_id, livekit_room, phone_number, trade, language,
                             scores, avg_score, fitment, weak_topics, feedback,
                             transcript, status, completed_at)
                        VALUES
                            (:candidate_id, :livekit_room, :phone_number, :trade, :language,
                             :scores, :avg_score, :fitment, :weak_topics, :feedback,
                             :transcript, :status, :completed_at)
                        RETURNING id
                    """),
                    {
                        "candidate_id": candidate_id,
                        "livekit_room": livekit_room or "",
                        "phone_number": phone_number or "",
                        "trade": trade or "",
                        "language": language,
                        "scores": json.dumps(scores),
                        "avg_score": average_score,
                        "fitment": fitment,
                        "weak_topics": json.dumps(weak_topics),
                        "feedback": json.dumps(feedback) if feedback else None,
                        "transcript": json.dumps(transcript or []),
                        "status": status,
                        "completed_at": completed_at,
                    },
                )
                record_id = result.fetchone()[0]

            conn.commit()
            logger.info(f"[DB] Saved interview result — id={record_id}, fitment={fitment}, avg={average_score}")
            return record_id

    except Exception as e:
        logger.error(f"[DB] save_result failed: {e}")
        raise


def check_integrity_flag(scores: list, avg: float) -> bool:
    """
    Returns True if the score pattern looks suspicious (possible cheating / error).
    Flags for manual review when:
      - All scores are identical (suspiciously uniform)
      - Avg is perfect 10 with more than 3 questions
      - More than half the scores are 0 (possible connectivity issue)
    """
    if not scores or len(scores) < 2:
        return False

    # All identical scores on 5+ questions is suspicious
    if len(scores) >= 5 and len(set(scores)) == 1:
        return True

    # Perfect 10 average on many questions
    if avg == 10.0 and len(scores) > 3:
        return True

    # More than half zeros — likely connectivity / STT failure
    zero_count = sum(1 for s in scores if s == 0)
    if zero_count > len(scores) / 2:
        return True

    return False
