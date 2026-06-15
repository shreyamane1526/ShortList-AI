from __future__ import annotations

from typing import List

from models import IntegrityFlag


def calculate_trust_score(
    commit_audit: dict,
    consistency_audit: dict,
    similarity_audit: dict,
    authorship_audit: dict,
    account_health_audit: dict,
) -> dict:
    """Combine all audit signals into a 0-100 trust score with labelled flags.

    Deduction caps prevent any single signal from dominating the score.
    The score reflects evidence authenticity, not skill level.
    """
    score = 100
    flags: List[IntegrityFlag] = []

    # --- clone risk: -15 per repo, max -40 ---
    clone_repos = commit_audit.get("clone_risk_repos", [])
    clone_deduction = min(len(clone_repos) * 15, 40)
    score -= clone_deduction
    for repo in clone_repos:
        flags.append(IntegrityFlag(
            flag_type="clone_risk",
            severity="high",
            detail=f"Repo '{repo}' shows multiple clone signals (low commits + generic message + low spread)",
        ))

    # --- skill jump: -20 ---
    if consistency_audit.get("skill_jump_detected"):
        score -= 20
        flags.append(IntegrityFlag(
            flag_type="skill_jump",
            severity="medium",
            detail=consistency_audit.get("jump_details", "Unusual complexity jump detected between repos"),
        ))

    # --- tutorial similarity: -10 per repo, max -30 ---
    flagged_similar = similarity_audit.get("flagged_repos", [])
    similarity_deduction = min(len(flagged_similar) * 10, 30)
    score -= similarity_deduction
    for item in flagged_similar:
        flags.append(IntegrityFlag(
            flag_type="high_similarity",
            severity="medium",
            detail=f"Repo '{item['repo']}' matched tutorial template '{item['matched_reference']}' at {item['score']*100:.0f}%",
        ))

    # --- low commit consistency: -10 ---
    if commit_audit.get("commit_consistency") == "low":
        score -= 10
        flags.append(IntegrityFlag(
            flag_type="low_commit_consistency",
            severity="low",
            detail="Overall commit spread is low across repos — activity appears sporadic",
        ))

    # --- authorship mismatch: -15 per flagged repo, max -25 ---
    auth_flagged = authorship_audit.get("flagged_repos", [])
    auth_deduction = min(len(auth_flagged) * 15, 25)
    score -= auth_deduction
    for repo in auth_flagged:
        flags.append(IntegrityFlag(
            flag_type="authorship_mismatch",
            severity="high",
            detail=f"Repo '{repo}' commits are mostly from unrelated email addresses",
        ))

    # --- suspicious account age ratio: -10 (weak signal, low severity) ---
    if account_health_audit.get("suspicious_age_ratio"):
        score -= 10
        flags.append(IntegrityFlag(
            flag_type="account_health",
            severity="low",
            detail="Account is less than 90 days old but has a large number of active repos",
        ))

    return {
        "trust_score": max(0, score),
        "flags": [f.model_dump() for f in flags],
    }