"""
Confidence scoring logic for Feedback Agent.
"""

from __future__ import annotations


def compute_confidence_score(
    evidence: dict,
    insight: dict,
    role_fit: dict,
) -> dict:
    """
    confidence =
        trust_score   * 0.3 +
        fairness_score* 0.2 +
        overall_fit   * 0.5
    """

    integrity = (
        evidence.get("integrity")
        or {}
    )

    trust_score = float(
        integrity.get(
            "trust_score",
            50,
        )
        if isinstance(
            integrity,
            dict,
        )
        else 50
    )

    overall_fit = float(
        role_fit.get(
            "overall_fit_score",
            0.5,
        )
    ) * 100

    bias_audit = (
        insight.get(
            "bias_audit"
        )
        or {}
    )

    fairness_raw = (
        bias_audit.get(
            "fairness_score",
            0.7,
        )
        if isinstance(
            bias_audit,
            dict,
        )
        else 0.7
    )

    fairness_score = (
        float(fairness_raw)
        * 100
    )

    score = round(
        trust_score * 0.3
        + fairness_score * 0.2
        + overall_fit * 0.5
    )

    score = max(
        0,
        min(100, score),
    )

    if score > 70:
        level = "High"

    elif score >= 40:
        level = "Medium"

    else:
        level = "Low"

    factors: list[str] = []

    signals = (
        evidence.get("signals")
        or {}
    )

    if isinstance(
        signals,
        dict,
    ):

        cc = signals.get(
            "commit_consistency",
            "",
        )

        if cc == "high":
            factors.append(
                "GitHub activity high"
            )

        elif cc == "low":
            factors.append(
                "GitHub activity low"
            )

    if trust_score >= 75:

        factors.append(
            "Strong evidence integrity"
        )

    elif trust_score < 50:

        factors.append(
            "Evidence integrity concerns"
        )

    matched_count = len([
        sm for sm in (
            role_fit.get(
                "required_skills_matched"
            )
            or []
        )
        if sm.get("matched")
    ])

    total_count = len(
        role_fit.get(
            "required_skills_matched"
        )
        or []
    )

    if total_count:

        if (
            matched_count
            / total_count
        ) >= 0.7:

            factors.append(
                "Strong skill coverage"
            )

        else:

            factors.append(
                "Resume skills incomplete"
            )

    if not factors:

        factors.append(
            "Based on available evidence"
        )

    return {
        "score": score,
        "level": level,
        "factors": factors,
    }