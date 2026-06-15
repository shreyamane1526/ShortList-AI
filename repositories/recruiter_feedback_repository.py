"""
Recruiter feedback persistence.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import inspect, text
from sqlmodel import Session
from sqlmodel import select

from core.database import (
    engine,
    RecruiterFeedback,
)


def _ensure_schema() -> None:
    inspector = inspect(engine)
    table_name = RecruiterFeedback.__table__.name

    if table_name not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    migrations = {
        "ai_prediction_json": "TEXT",
        "prediction_score": "FLOAT",
        "jd_hash": "TEXT",
        "model_version": "TEXT",
    }

    with engine.begin() as connection:
        for column_name, column_type in migrations.items():
            if column_name not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )


def _prediction_summary(ai_prediction: Any) -> str:
    if isinstance(ai_prediction, dict):
        for key in (
            "status",
            "prediction",
            "recommendation",
            "decision",
        ):
            value = ai_prediction.get(key)
            if value is not None:
                return str(value)
        return json.dumps(ai_prediction, default=str)

    if ai_prediction is None:
        return "unknown"

    return str(ai_prediction)


def _prediction_score(ai_prediction: Any) -> float | None:
    if not isinstance(ai_prediction, dict):
        return None

    for key in (
        "composite_score",
        "score",
        "probability",
    ):
        value = ai_prediction.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return None


def save_recruiter_feedback(

    candidate_id: str,

    prediction: str | dict | None = None,

    recruiter_decision: str = "",

    override_reason: str | None = None,

    final_outcome: str | None = None,

    *,

    ai_prediction: dict | str | None = None,

    final_hiring_outcome: str | None = None,

    jd_hash: str | None = None,

    model_version: str | None = None,
):
    _ensure_schema()

    prediction_payload = (
        ai_prediction
        if ai_prediction is not None
        else prediction
    )

    final_outcome = (
        final_hiring_outcome
        if final_hiring_outcome is not None
        else final_outcome
    )

    row = RecruiterFeedback(

        candidate_id=candidate_id,

        prediction=_prediction_summary(
            prediction_payload
        ),

        ai_prediction_json=json.dumps(
            prediction_payload,
            default=str,
        ),

        prediction_score=_prediction_score(
            prediction_payload
        ),

        recruiter_decision=recruiter_decision,

        override_reason=override_reason,

        final_outcome=final_outcome,

        jd_hash=jd_hash,

        model_version=model_version,
    )

    with Session(engine) as session:

        session.add(
            row
        )

        session.commit()
        session.refresh(row)

    print(
        "[recruiter_feedback_repository] "
        "feedback stored"
    )

    return row


def list_recruiter_feedback() -> list[RecruiterFeedback]:
    _ensure_schema()

    with Session(engine) as session:
        return list(
            session.exec(
                select(RecruiterFeedback)
            ).all()
        )
