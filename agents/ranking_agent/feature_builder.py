from __future__ import annotations


def build_feature_vector(
    evidence: dict,
    role_fit: dict,
    insight: dict,
) -> dict:

    integrity = (
        evidence.get("integrity")
        or {}
    )

    trust_score = float(
        integrity.get(
            "trust_score",
            50,
        )
    )

    fit_score = float(
        role_fit.get(
            "overall_fit_score",
            0.0,
        )
    ) * 100.0

    reasoning_score = float(
        insight.get(
            "score",
            0,
        )
    )

    skill_gaps = (
        insight.get(
            "skill_gaps"
        )
        or []
    )

    critical_gaps = len([
        g for g in skill_gaps
        if isinstance(g, dict)
        and g.get("severity") == "critical"
    ])

    moderate_gaps = len([
        g for g in skill_gaps
        if isinstance(g, dict)
        and g.get("severity") == "moderate"
    ])

    nd_strengths = (
        insight.get(
            "nd_strengths"
        )
        or []
    )

    nd_count = len(nd_strengths)

    recommendation = str(
        insight.get(
            "recommendation",
            "no",
        )
    ).lower()

    recommendation_map = {
        "strong_yes": 3,
        "yes": 2,
        "maybe": 1,
        "no": 0,
    }

    recommendation_score = (
        recommendation_map.get(
            recommendation,
            0,
        )
    )

    return {
        "reasoning_score": reasoning_score,
        "fit_score": fit_score,
        "trust_score": trust_score,
        "critical_gaps": critical_gaps,
        "moderate_gaps": moderate_gaps,
        "nd_strengths": nd_count,
        "recommendation_score": recommendation_score,
    }