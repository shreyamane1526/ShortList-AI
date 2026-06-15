from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List


def audit_commits(repos: list) -> dict:
    """Analyze commit patterns across repos for authenticity signals.

    Computes a spread score (unique commit days / repo age) per repo.
    Commit bursts are treated as a weak signal only — genuine local-first
    developers often push everything at once. A burst alone never triggers
    clone_risk; it must be combined with other weak signals (low commit count
    + generic first message).
    """
    clone_risk_repos: List[str] = []
    spread_scores: Dict[str, float] = {}
    all_spreads: List[float] = []

    for repo in repos:
        name = repo.get("name", "unknown")
        commit_dates_raw: List[str] = repo.get("commit_dates", [])
        commit_messages: List[str] = repo.get("commit_messages", [])
        commit_count: int = repo.get("commit_count", 0)

        if not commit_dates_raw:
            spread_scores[name] = 0.0
            continue

        dates = _parse_dates(commit_dates_raw)
        if not dates:
            spread_scores[name] = 0.0
            continue

        unique_days = len(set(d.date() for d in dates))
        repo_age_days = max(1, (max(dates) - min(dates)).days)
        spread = unique_days / repo_age_days
        spread_scores[name] = round(spread, 4)
        all_spreads.append(spread)

        # --- clone risk: needs multiple weak signals, not just burst ---
        weak_signals = 0

        # weak signal 1: very few commits
        if commit_count <= 3:
            weak_signals += 1

        # weak signal 2: first commit message is generic
        first_msg = (commit_messages[0] if commit_messages else "").lower()
        if any(kw in first_msg for kw in ["initial", "init", "first commit", "initial commit"]):
            weak_signals += 1

        # weak signal 3: extremely low spread (all commits clustered in one window)
        if spread < 0.03 and repo_age_days > 7:
            weak_signals += 1

        # only flag as clone risk if 2+ weak signals — protects local-first devs
        if weak_signals >= 2:
            clone_risk_repos.append(name)

    average_spread = round(sum(all_spreads) / len(all_spreads), 4) if all_spreads else 0.0

    if average_spread > 0.3:
        consistency = "high"
    elif average_spread >= 0.1:
        consistency = "medium"
    else:
        consistency = "low"

    return {
        "clone_risk_repos": clone_risk_repos,
        "spread_scores": spread_scores,
        "average_spread": average_spread,
        "commit_consistency": consistency,
    }


def _parse_dates(raw: List[str]) -> List[datetime]:
    """Parse ISO date strings into datetime objects, skipping malformed entries."""
    parsed = []
    for s in raw:
        if not s:
            continue
        try:
            # GitHub returns ISO 8601 with Z suffix
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            parsed.append(dt)
        except ValueError:
            continue
    return parsed