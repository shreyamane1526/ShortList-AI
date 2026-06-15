from __future__ import annotations

from datetime import datetime
from typing import Dict, List


def audit_consistency(repos: list) -> dict:
    """Detect suspicious complexity jumps between consecutive repos over time.

    Complexity is estimated from code sample count, commit count, and language
    diversity. A jump of 3.5x or more between adjacent repos (by creation date)
    is flagged as a skill_jump. Single large jumps in a long history are less
    suspicious than early jumps — future versions can weight by index.
    """
    if len(repos) < 2:
        return {
            "skill_jump_detected": False,
            "jump_details": "",
            "complexity_scores": {r.get("name", "?"): _score(r) for r in repos},
        }

    sorted_repos = sorted(repos, key=lambda r: r.get("created_at", ""))

    complexity_scores: Dict[str, float] = {}
    for repo in sorted_repos:
        complexity_scores[repo.get("name", "?")] = _score(repo)

    jump_details: List[str] = []
    for i in range(len(sorted_repos) - 1):
        a = sorted_repos[i]
        b = sorted_repos[i + 1]
        score_a = complexity_scores[a.get("name", "?")]
        score_b = complexity_scores[b.get("name", "?")]

        if score_a > 0 and score_b > score_a * 3.5:
            jump_details.append(
                f"Complexity jumped from {score_a:.1f} to {score_b:.1f} "
                f"between '{a.get('name')}' and '{b.get('name')}'"
            )

    return {
        "skill_jump_detected": len(jump_details) > 0,
        "jump_details": "; ".join(jump_details),
        "complexity_scores": complexity_scores,
    }


def _score(repo: dict) -> float:
    """Estimate repo complexity from observable signals."""
    code_samples = len(repo.get("code_samples", []))
    commit_count = repo.get("commit_count", 0)
    languages = len(repo.get("languages", {}))
    return (code_samples * 10) + (commit_count * 0.5) + (languages * 5)