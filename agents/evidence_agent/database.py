from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = "sqlite:///./evidence_agent.db"
engine = create_engine(DATABASE_URL, echo=False)

CACHE_TTL_HOURS = 24


class CandidateCache(SQLModel, table=True):
    """Stores serialized SkillProfile JSON with a TTL so other agents can query without re-scraping."""

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: str = Field(index=True, unique=True)
    schema_version: str = "1.0"
    profile_json: str        # full SkillProfile serialized as JSON string
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
    )


def init_db() -> None:
    """Create tables on startup."""
    SQLModel.metadata.create_all(engine)


def save_profile(candidate_id: str, profile_dict: dict) -> None:
    """Upsert a SkillProfile into the cache."""
    with Session(engine) as session:
        existing = session.exec(
            select(CandidateCache).where(CandidateCache.candidate_id == candidate_id)
        ).first()

        now = datetime.utcnow()
        expires = now + timedelta(hours=CACHE_TTL_HOURS)

        if existing:
            existing.profile_json = json.dumps(profile_dict, default=str)
            existing.collected_at = now
            existing.ttl_expires_at = expires
            existing.schema_version = profile_dict.get("schema_version", "1.0")
            session.add(existing)
        else:
            record = CandidateCache(
                candidate_id=candidate_id,
                schema_version=profile_dict.get("schema_version", "1.0"),
                profile_json=json.dumps(profile_dict, default=str),
                collected_at=now,
                ttl_expires_at=expires,
            )
            session.add(record)

        session.commit()


def get_profile(candidate_id: str) -> Optional[dict]:
    """Return cached SkillProfile dict if it exists and hasn't expired."""
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
    """Check whether a fresh cached profile exists for this candidate."""
    return get_profile(candidate_id) is not None