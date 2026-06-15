"""
core/database.py  — MODIFIED FILE (migrated from Agent 1's database.py)

Changes from original Agent 1 database.py:
  1. DATABASE_URL now read from settings (supports both PostgreSQL + SQLite)
  2. Engine creation uses connect_args conditionally — psycopg2 for PG, check_same_thread for SQLite
  3. Schema is UNCHANGED — CandidateCache table is identical
  4. All function signatures unchanged — Agent 1 code needs zero modifications

PostgreSQL connection string format (set in .env):
  DATABASE_URL=postgresql://user:password@localhost:5432/shortlist_ai

SQLite fallback (no DATABASE_URL in .env):
  DATABASE_URL=sqlite:///./shortlist_ai.db
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import psycopg2
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import UniqueConstraint

from core.config import settings

# ── Engine — auto-selects dialect from DATABASE_URL ───────────────────────────
def _make_engine():
    url = settings.DATABASE_URL
    if url.startswith("postgresql"):
        # psycopg2 — no extra connect_args needed
        return create_engine(url, echo=settings.DEBUG)
    else:
        # SQLite — must allow multi-thread access for FastAPI
        return create_engine(url, echo=settings.DEBUG,
                             connect_args={"check_same_thread": False})


engine = _make_engine()

CACHE_TTL_HOURS = settings.CACHE_TTL_HOURS



def get_connection():

    """
    Shared PostgreSQL connection factory.
    """

    return psycopg2.connect(
        settings.DATABASE_URL
    )

def compute_jd_hash(jd: str) -> str:
    """Compute a hash for the job description."""
    return hashlib.sha256(jd.encode('utf-8')).hexdigest()


# ── Table definition — UNCHANGED from original Agent 1 ───────────────────────

class CandidateCache(SQLModel, table=True):
    """
    Stores serialized SkillProfile JSON with a TTL.
    Downstream agents query this instead of re-scraping GitHub.

    PostgreSQL: uses TEXT column for profile_json (identical to SQLite).
    """
    id: Optional[int]         = Field(default=None, primary_key=True)
    candidate_id: str          = Field(index=True, unique=True)
    schema_version: str        = "1.0"
    profile_json: str          # full CandidateEvidence serialized as JSON
    collected_at: datetime     = Field(default_factory=datetime.utcnow)
    ttl_expires_at: datetime   = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
    )


class CandidateScore(SQLModel, table=True):
    """
    Stores computed ranking scores for candidates against a specific job description.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    jd_hash: str = Field(index=True)
    candidate_id: str = Field(index=True)
    github: str
    leetcode: str
    composite_score: float
    tier: str
    status: str
    rationale: str
    components: str  # JSON string of the components dict
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (UniqueConstraint("jd_hash", "candidate_id"),)


class FeedbackReport(SQLModel, table=True):
    """
    Agent 5 output — rich structured feedback linked to a pipeline run.

    evaluation_id is a logical key: (jd_hash + candidate_id) hashed together,
    or any string that uniquely identifies one pipeline run.  The FastAPI
    /api/feedback/<evaluation_id> endpoint uses this to look up the report.
    """
    __tablename__ = "feedback_reports"

    id: Optional[int]  = Field(default=None, primary_key=True)
    evaluation_id: str = Field(index=True, unique=True)   # jd_hash:candidate_id

    # Full structured JSON blob (the complete feedback dict)
    feedback_json: str                          # JSON-serialised feedback dict

    # Denormalised fast-access fields
    confidence_score: Optional[int]  = None    # 0-100
    confidence_level: Optional[str]  = None    # Low / Medium / High
    badges_json: Optional[str]       = None    # JSON array of badge strings

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_time_ms: Optional[int] = None

class RecruiterFeedback(SQLModel, table=True):

    """
    Human recruiter override feedback.

    This becomes the ground-truth dataset
    for future retraining.
    """

    model_config = {
        "protected_namespaces": (),
    }

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    candidate_id: str = Field(
        index=True,
    )

    prediction: str

    ai_prediction_json: Optional[str] = None

    prediction_score: Optional[float] = None

    recruiter_decision: str

    override_reason: Optional[str] = None

    final_outcome: Optional[str] = None

    jd_hash: Optional[str] = Field(
        default=None,
        index=True,
    )

    model_version: Optional[str] = None

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class FeatureStoreRecord(SQLModel, table=True):

    """
    Centralized ML feature snapshot.

    Rows join model inputs, predictions, and later recruiter labels
    so retraining can use the same schema served in production.
    """

    __tablename__ = "feature_store"

    model_config = {
        "protected_namespaces": (),
    }

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    candidate_id: str = Field(
        index=True,
    )

    jd_hash: Optional[str] = Field(
        default=None,
        index=True,
    )

    role_fit_score: float = 0.0

    reasoning_score: float = 0.0

    trust_score: float = 0.0

    embedding_score: Optional[float] = None

    nd_indicators_json: str = "[]"

    recruiter_outcome: Optional[str] = None

    recruiter_decision: Optional[str] = None

    model_prediction: Optional[str] = None

    model_prediction_score: Optional[float] = None

    model_version: Optional[str] = None

    feature_schema_json: str = "{}"

    raw_features_json: str = "{}"

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

def init_db() -> None:
    """Create tables. Called once at FastAPI startup."""
    SQLModel.metadata.create_all(engine)
    db_type = "PostgreSQL" if settings.is_postgres else "SQLite"
    print(f"  [DB] {db_type} tables ready")


def save_profile(candidate_id: str, profile_dict: dict) -> None:
    """Upsert a CandidateEvidence dict into the cache."""
    with Session(engine) as session:
        existing = session.exec(
            select(CandidateCache).where(CandidateCache.candidate_id == candidate_id)
        ).first()

        now     = datetime.utcnow()
        expires = now + timedelta(hours=CACHE_TTL_HOURS)
        blob    = json.dumps(profile_dict, default=str)

        if existing:
            existing.profile_json    = blob
            existing.collected_at    = now
            existing.ttl_expires_at  = expires
            existing.schema_version  = profile_dict.get("schema_version", "1.0")
            session.add(existing)
        else:
            session.add(CandidateCache(
                candidate_id   = candidate_id,
                schema_version = profile_dict.get("schema_version", "1.0"),
                profile_json   = blob,
                collected_at   = now,
                ttl_expires_at = expires,
            ))
        session.commit()


def get_profile(candidate_id: str) -> Optional[dict]:
    """Return cached CandidateEvidence dict if not expired. None otherwise."""
    with Session(engine) as session:
        record = session.exec(
            select(CandidateCache).where(CandidateCache.candidate_id == candidate_id)
        ).first()
        if record is None:
            return None
        if datetime.utcnow() > record.ttl_expires_at:
            return None
        return json.loads(record.profile_json)


def is_cache_valid(candidate_id: str) -> bool:
    return get_profile(candidate_id) is not None


def save_score(jd_hash: str, candidate_id: str, github: str, leetcode: str, score_data: dict) -> None:
    """Save or update candidate score for a JD."""
    with Session(engine) as session:
        existing = session.exec(
            select(CandidateScore).where(
                CandidateScore.jd_hash == jd_hash,
                CandidateScore.candidate_id == candidate_id
            )
        ).first()

        components_json = json.dumps(score_data["components"], default=str)

        if existing:
            existing.composite_score = score_data["composite_score"]
            existing.tier = score_data["tier"]
            existing.status = score_data["status"]
            existing.rationale = score_data["rationale"]
            existing.components = components_json
            existing.created_at = datetime.utcnow()
            session.add(existing)
        else:
            session.add(CandidateScore(
                jd_hash=jd_hash,
                candidate_id=candidate_id,
                github=github,
                leetcode=leetcode,
                composite_score=score_data["composite_score"],
                tier=score_data["tier"],
                status=score_data["status"],
                rationale=score_data["rationale"],
                components=components_json,
            ))
        session.commit()


def get_scores_for_jd(jd_hash: str) -> list[dict]:
    """Get all scores for a JD."""
    with Session(engine) as session:
        records = session.exec(
            select(CandidateScore).where(CandidateScore.jd_hash == jd_hash)
        ).all()
        scores = []
        for record in records:
            scores.append({
                "candidate_id": record.candidate_id,
                "github": record.github,
                "leetcode": record.leetcode,
                "composite_score": record.composite_score,
                "tier": record.tier,
                "status": record.status,
                "rationale": record.rationale,
                "components": json.loads(record.components),
                "created_at": record.created_at,
            })
        return scores


def get_score(jd_hash: str, candidate_id: str) -> Optional[dict]:
    """Get score for a specific candidate and JD."""
    with Session(engine) as session:
        record = session.exec(
            select(CandidateScore).where(
                CandidateScore.jd_hash == jd_hash,
                CandidateScore.candidate_id == candidate_id
            )
        ).first()
        if record:
            return {
                "candidate_id": record.candidate_id,
                "github": record.github,
                "leetcode": record.leetcode,
                "composite_score": record.composite_score,
                "tier": record.tier,
                "status": record.status,
                "rationale": record.rationale,
                "components": json.loads(record.components),
                "created_at": record.created_at,
            }
        return None


def _make_evaluation_id(jd_hash: str, candidate_id: str) -> str:
    """Canonical evaluation_id used as the primary key for FeedbackReport."""
    return f"{jd_hash}:{candidate_id}"


def save_feedback_report(
    jd_hash: str,
    candidate_id: str,
    feedback_dict: dict,
    generation_time_ms: Optional[int] = None,
) -> str:
    """
    Upsert a FeedbackReport row.

    Returns the evaluation_id string so callers can pass it to the API.
    """
    import time as _time

    evaluation_id = _make_evaluation_id(jd_hash, candidate_id)
    feedback_json = json.dumps(feedback_dict, default=str)
    confidence    = feedback_dict.get("confidence_score") or {}
    badges        = feedback_dict.get("badges") or []

    with Session(engine) as session:
        existing = session.exec(
            select(FeedbackReport).where(FeedbackReport.evaluation_id == evaluation_id)
        ).first()

        if existing:
            existing.feedback_json       = feedback_json
            existing.confidence_score    = confidence.get("score")
            existing.confidence_level    = confidence.get("level")
            existing.badges_json         = json.dumps(badges)
            existing.generated_at        = datetime.utcnow()
            existing.generation_time_ms  = generation_time_ms
            session.add(existing)
        else:
            session.add(FeedbackReport(
                evaluation_id      = evaluation_id,
                feedback_json      = feedback_json,
                confidence_score   = confidence.get("score"),
                confidence_level   = confidence.get("level"),
                badges_json        = json.dumps(badges),
                generation_time_ms = generation_time_ms,
            ))
        session.commit()

    return evaluation_id


def get_feedback_report(evaluation_id: str) -> Optional[dict]:
    """
    Retrieve a FeedbackReport by evaluation_id.
    Returns the full feedback dict, or None if not found.
    """
    with Session(engine) as session:
        record = session.exec(
            select(FeedbackReport).where(FeedbackReport.evaluation_id == evaluation_id)
        ).first()
        if record is None:
            return None
        data = json.loads(record.feedback_json)
        data["_meta"] = {
            "evaluation_id":     record.evaluation_id,
            "generated_at":      record.generated_at.isoformat(),
            "generation_time_ms": record.generation_time_ms,
        }
        return data


def get_feedback_report_by_candidate(jd_hash: str, candidate_id: str) -> Optional[dict]:
    """Convenience wrapper — look up by (jd_hash, candidate_id) pair."""
    return get_feedback_report(_make_evaluation_id(jd_hash, candidate_id))

# Add this at the bottom of core/database.py
def get_db():
    """FastAPI dependency that provides a database session."""
    with Session(engine) as session:
        yield session
