"""
Feature store persistence for ranking training and analytics.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import inspect, text
from sqlmodel import Session, select

from core.database import (
    FeatureStoreRecord,
    engine,
)


FEATURE_SCHEMA_VERSION = "ranking_features_v1"


def _ensure_schema() -> None:
    inspector = inspect(engine)
    table_name = FeatureStoreRecord.__table__.name

    if table_name not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    migrations = {
        "jd_hash": "TEXT",
        "role_fit_score": "FLOAT DEFAULT 0",
        "reasoning_score": "FLOAT DEFAULT 0",
        "trust_score": "FLOAT DEFAULT 0",
        "embedding_score": "FLOAT",
        "nd_indicators_json": "TEXT DEFAULT '[]'",
        "recruiter_outcome": "TEXT",
        "recruiter_decision": "TEXT",
        "model_prediction": "TEXT",
        "model_prediction_score": "FLOAT",
        "model_version": "TEXT",
        "feature_schema_json": "TEXT DEFAULT '{}'",
        "raw_features_json": "TEXT DEFAULT '{}'",
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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _nd_indicators(features: dict, insight: dict | None) -> list[str]:
    indicators: list[str] = []

    if features.get("nd_strengths"):
        indicators.append(
            f"nd_strengths:{features['nd_strengths']}"
        )

    if insight:
        bias_audit = insight.get("bias_audit") or {}
        if bias_audit.get("nd_signal_detected"):
            indicators.append("nd_signal_detected")

        for item in insight.get("nd_strengths") or []:
            if isinstance(item, dict) and item.get("signal"):
                indicators.append(str(item["signal"]))

    return indicators


def save_feature_snapshot(
    candidate_id: str,
    features: dict,
    prediction: dict | None = None,
    insight: dict | None = None,
    jd_hash: str | None = None,
    recruiter_decision: str | None = None,
    recruiter_outcome: str | None = None,
    model_version: str | None = None,
) -> FeatureStoreRecord:
    _ensure_schema()

    prediction = prediction or {}
    feature_schema = {
        "version": FEATURE_SCHEMA_VERSION,
        "columns": list(features.keys()),
    }

    row = FeatureStoreRecord(
        candidate_id=candidate_id,
        jd_hash=jd_hash,
        role_fit_score=_as_float(
            features.get("fit_score")
            or features.get("role_fit_score")
        ),
        reasoning_score=_as_float(
            features.get("reasoning_score")
        ),
        trust_score=_as_float(
            features.get("trust_score")
        ),
        embedding_score=_as_float(
            features.get("embedding_score"),
            default=None,
        ),
        nd_indicators_json=json.dumps(
            _nd_indicators(features, insight),
            default=str,
        ),
        recruiter_outcome=recruiter_outcome,
        recruiter_decision=recruiter_decision,
        model_prediction=prediction.get("status"),
        model_prediction_score=_as_float(
            prediction.get("composite_score"),
            default=None,
        ),
        model_version=model_version,
        feature_schema_json=json.dumps(
            feature_schema,
            default=str,
        ),
        raw_features_json=json.dumps(
            features,
            default=str,
        ),
    )

    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

    return row


def list_feature_snapshots() -> list[FeatureStoreRecord]:
    _ensure_schema()

    with Session(engine) as session:
        return list(
            session.exec(
                select(FeatureStoreRecord)
            ).all()
        )
