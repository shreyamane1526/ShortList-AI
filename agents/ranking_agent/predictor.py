from __future__ import annotations

import joblib
import pandas as pd


MODEL_PATH = (
    "agents/ranking_agent/"
    "models/xgb_model.pkl"
)


model = joblib.load(
    MODEL_PATH
)


def predict_score(
    features: dict,
) -> dict:

    X = pd.DataFrame(
        [features]
    )

    probability = (
        model.predict_proba(X)[0][1]
    )

    score = round(
        probability * 100,
        2,
    )

    status = (
        "shortlisted"
        if score >= 50
        else "rejected"
    )

    tier = (
        "strong"
        if score >= 75
        else "qualified"
        if score >= 50
        else "below_bar"
    )

    return {

        "composite_score": score,

        "status": status,

        "tier": tier,

        "rationale": (
            "ML-based ranking prediction "
            "using XGBoost."
        ),

        "components": {

            "raw_reasoning_score": features.get(
                "reasoning_score",
                0,
            ),

            "raw_fit_score": features.get(
                "fit_score",
                0,
            ),

            "raw_trust_score": features.get(
                "trust_score",
                0,
            ),

            "nd_strengths_count": features.get(
                "nd_strengths",
                0,
            ),

            "recommendation": features.get(
                "recommendation_score",
                0,
            ),
        },
    }