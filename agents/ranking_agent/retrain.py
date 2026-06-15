"""
Continuous retraining pipeline for the ranking model.

Recruiter feedback is treated as the ground-truth label source.
Feature snapshots provide the production feature matrix.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from core.database import init_db
from repositories.feature_store_repository import (
    FEATURE_SCHEMA_VERSION,
    list_feature_snapshots,
)
from repositories.recruiter_feedback_repository import (
    list_recruiter_feedback,
)

from models.registry.registry import (
    ModelPaths,
    ensure_registry_dirs,
    read_model_metadata_by_version,
    write_current_model,
)
from models.validation.validator import (
    build_validation_result,
    should_promote,
)



BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
MODEL_DIR = BASE_DIR / "models"
ACTIVE_MODEL_PATH = MODEL_DIR / "xgb_model.pkl"
REGISTRY_DIR = PROJECT_ROOT / "models" / "registry"
CURRENT_MODEL_PATH = PROJECT_ROOT / "models" / "current_model.json"

FEATURE_COLUMNS = [
    "reasoning_score",
    "fit_score",
    "trust_score",
    "critical_gaps",
    "moderate_gaps",
    "nd_strengths",
    "recommendation_score",
]

POSITIVE_LABELS = {
    "advance",
    "advanced",
    "hire",
    "hired",
    "interview",
    "offer",
    "select",
    "selected",
    "shortlist",
    "shortlisted",
    "yes",
}

NEGATIVE_LABELS = {
    "decline",
    "declined",
    "no",
    "reject",
    "rejected",
}


def _normalize_label(*values: str | None) -> int | None:
    for value in values:
        if not value:
            continue

        normalized = value.strip().lower()
        if normalized in POSITIVE_LABELS:
            return 1
        if normalized in NEGATIVE_LABELS:
            return 0

    return None


def _safe_json_loads(payload: str | None, default):
    if not payload:
        return default

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return default


def _fallback_features(row) -> dict:
    prediction = (row.prediction or "").lower()
    score = row.prediction_score

    if score is None:
        score = 100.0 if prediction in POSITIVE_LABELS else 0.0

    return {
        "reasoning_score": 0.0,
        "fit_score": 0.0,
        "trust_score": 50.0,
        "critical_gaps": 0.0,
        "moderate_gaps": 0.0,
        "nd_strengths": 0.0,
        "recommendation_score": 1.0 if score >= 50 else 0.0,
    }


def _feature_key(candidate_id: str, jd_hash: str | None) -> tuple[str, str | None]:
    return (
        candidate_id,
        jd_hash,
    )


def _latest_feature_maps():
    by_candidate_and_jd: dict[tuple[str, str | None], object] = {}
    by_candidate: dict[str, object] = {}

    for row in list_feature_snapshots():
        key = _feature_key(
            row.candidate_id,
            row.jd_hash,
        )

        current = by_candidate_and_jd.get(key)
        if current is None or row.created_at > current.created_at:
            by_candidate_and_jd[key] = row

        candidate_current = by_candidate.get(row.candidate_id)
        if candidate_current is None or row.created_at > candidate_current.created_at:
            by_candidate[row.candidate_id] = row

    return by_candidate_and_jd, by_candidate


def build_training_frame() -> pd.DataFrame:
    feedback_rows = list_recruiter_feedback()
    by_candidate_and_jd, by_candidate = _latest_feature_maps()
    dataset: list[dict] = []

    for feedback in feedback_rows:
        label = _normalize_label(
            feedback.final_outcome,
            feedback.recruiter_decision,
        )
        if label is None:
            continue

        feature_row = by_candidate_and_jd.get(
            _feature_key(
                feedback.candidate_id,
                feedback.jd_hash,
            )
        ) or by_candidate.get(
            feedback.candidate_id
        )

        if feature_row:
            features = _safe_json_loads(
                feature_row.raw_features_json,
                {},
            )
            nd_indicators = _safe_json_loads(
                feature_row.nd_indicators_json,
                [],
            )
        else:
            features = _fallback_features(feedback)
            nd_indicators = []

        row = {
            column: float(features.get(column, 0.0) or 0.0)
            for column in FEATURE_COLUMNS
        }
        row["has_nd_signal"] = 1 if nd_indicators else 0
        row["label"] = label
        dataset.append(row)

    return pd.DataFrame(dataset)


def _next_model_version() -> int:
    REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    versions = []
    for path in REGISTRY_DIR.glob("xgb_model_v*.pkl"):
        suffix = path.stem.replace("xgb_model_v", "")
        if suffix.isdigit():
            versions.append(int(suffix))

    return max(versions, default=0) + 1


def _fairness_score(groups: pd.Series, preds) -> float:
    if groups.empty:
        return 1.0

    scored = pd.DataFrame(
        {
            "has_nd_signal": groups,
        }
    )
    scored["prediction"] = preds
    grouped = scored.groupby("has_nd_signal")["prediction"].mean()

    if len(grouped) < 2:
        return 1.0

    disparity = abs(float(grouped.max()) - float(grouped.min()))
    return round(max(0.0, 1.0 - disparity), 4)


# NOTE: validation/promotion logic is now delegated to models.validation.validator
# NOTE: model registry metadata writing/promotion pointer is now delegated to models.registry.registry



def retrain_model() -> dict | None:
    print("\n[Retraining] Loading recruiter labels and feature snapshots...")
    init_db()

    df = build_training_frame()
    if df.empty:
        print("[Retraining] No labeled recruiter feedback found.")
        return None

    if df["label"].nunique() < 2:
        print("[Retraining] Need at least two label classes before training.")
        return None

    X = df[FEATURE_COLUMNS]
    y = df["label"]
    groups = df["has_nd_signal"]

    class_counts = y.value_counts()
    can_stratify = len(df) >= 5 and class_counts.min() >= 2

    if can_stratify:
        X_train, X_test, y_train, y_test, _, groups_test = train_test_split(
            X,
            y,
            groups,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
        groups_test = groups

    print("[Retraining] Training XGBoost...")

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
    )

    preds = model.predict(X_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "precision": round(
            float(
                precision_score(
                    y_test,
                    preds,
                    zero_division=0,
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    y_test,
                    preds,
                    zero_division=0,
                )
            ),
            4,
        ),
        "fairness_score": _fairness_score(
            groups_test,
            preds,
        ),
        "drift_score": 1.0,
        "training_size": int(len(X_train)),
        "evaluation_size": int(len(X_test)),
    }

    validation = build_validation_result(metrics).as_dict()
    version = _next_model_version()

    versioned_model_path = REGISTRY_DIR / f"xgb_model_v{version}.pkl"
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        versioned_model_path,
    )

    promoted = should_promote(build_validation_result(metrics))

    if promoted:
        shutil.copy2(
            versioned_model_path,
            ACTIVE_MODEL_PATH,
        )
        shutil.copy2(
            versioned_model_path,
            MODEL_DIR / f"xgb_model_v{version}.pkl",
        )

    metadata = {
        "model_version": f"v{version}",
        "training_date": datetime.utcnow().isoformat(),
        "dataset_size": len(df),
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "fairness_score": metrics["fairness_score"],
        "drift_score": metrics["drift_score"],
        "feature_schema": {
            "version": FEATURE_SCHEMA_VERSION,
            "columns": FEATURE_COLUMNS,
        },
        "validation": validation,
        "promoted": promoted,
    }

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    metadata_path = REGISTRY_DIR / f"xgb_model_v{version}.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    if promoted:
        write_current_model(
            ModelPaths.from_repo_root(PROJECT_ROOT),
            version=version,
            metadata=metadata,
        )


    print(
        f"[Retraining] Metrics: "
        f"accuracy={metrics['accuracy']:.4f}, "
        f"precision={metrics['precision']:.4f}, "
        f"recall={metrics['recall']:.4f}"
    )
    print(
        f"[Retraining] Model saved -> {versioned_model_path}"
    )
    print(
        f"[Retraining] Metadata saved -> {metadata_path}"
    )

    if promoted:
        print(
            f"[Retraining] Promoted active model -> {ACTIVE_MODEL_PATH}"
        )
    else:
        print(
            "[Retraining] Model not promoted: "
            + "; ".join(validation["issues"])
        )

    return {
        "model_version": f"v{version}",
        "model_path": str(versioned_model_path),
        "metadata_path": str(metadata_path),
        "metrics": metrics,
        "validation": validation,
        "promoted": promoted,
    }


if __name__ == "__main__":
    retrain_model()
