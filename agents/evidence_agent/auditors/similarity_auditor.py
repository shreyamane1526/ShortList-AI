from __future__ import annotations

import json
import os
from typing import Dict, List

REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "reference_repos.json")
SIMILARITY_THRESHOLD = 0.6


def audit_similarity(repos: list) -> dict:
    """Compare each repo's text content against known tutorial project keyword lists.

    Uses term-overlap (matching keywords / total keywords) rather than neural
    embeddings — no API cost, runs fully offline. Flags repos above 0.6 overlap.
    """
    reference_repos = _load_references()

    flagged: List[Dict] = []
    highest = 0.0

    for repo in repos:
        blob = _build_text_blob(repo).lower()

        for ref in reference_repos:
            keywords: List[str] = ref["keywords"]
            if not keywords:
                continue

            matches = sum(1 for kw in keywords if kw.lower() in blob)
            score = matches / len(keywords)

            if score > SIMILARITY_THRESHOLD:
                flagged.append({
                    "repo": repo.get("name", "unknown"),
                    "matched_reference": ref["name"],
                    "score": round(score, 3),
                })
                if score > highest:
                    highest = score

    return {
        "flagged_repos": flagged,
        "highest_similarity": round(highest, 3),
    }


def _build_text_blob(repo: dict) -> str:
    """Combine all textual repo signals into one string for keyword matching."""
    parts = [
        repo.get("name", ""),
        repo.get("description", ""),
        " ".join(repo.get("commit_messages", [])),
        " ".join(repo.get("code_samples", [])),
    ]
    return " ".join(parts)


def _load_references() -> list:
    """Load reference repo keyword lists from JSON file."""
    try:
        with open(REFERENCE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []