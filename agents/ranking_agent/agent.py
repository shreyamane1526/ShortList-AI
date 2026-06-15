"""
agents/ranking_agent/agent.py  —  Agent 4

LangGraph node that slots directly into your existing pipeline.py.

It reads from GraphState:
    state["evidence"]   — written by Agent 1
    state["role_fit"]   — written by Agent 2
    state["insight"]    — written by Agent 3

It writes to GraphState:
    state["ranking"]    — ShortlistResult dict

Single-candidate mode (one person through the pipeline):
    Scores that one candidate, marks shortlisted/rejected,
    writes justification, saves to DB.

Multi-candidate mode (batch via API):
    Call rank_batch() directly — see api/main.py.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from repositories.training_repository import (
    save_training_example,
)
from repositories.feature_store_repository import (
    save_feature_snapshot,
)
from .scorer import compute_score
from .llm_justifier import generate_justification

from .feature_builder import (
    build_feature_vector,
)

from .predictor import (
    predict_score,
)

# DB import — same pattern as reasoning_agent
try:
    from core.database import (
        save_score,
        compute_jd_hash,
    )

    DB_AVAILABLE = True

except ImportError:

    DB_AVAILABLE = False


def ranking_agent_node(state: dict) -> dict:
    """
    LangGraph node — drop-in replacement for ranking_agent_stub in pipeline.py.

    Reads evidence / role_fit / insight from state.
    Writes ranking dict back to state.
    """

    errors: list = list(
        state.get("errors", [])
    )

    evidence = (
        state.get("evidence")
        or {}
    )

    role_fit = (
        state.get("role_fit")
        or {}
    )

    insight = (
        state.get("insight")
        or {}
    )

    if not insight:

        err = (
            "ranking_agent: no insight in state "
            "— Agent 3 may have failed"
        )

        print(
            f"  [Agent 4] ⚠  {err}"
        )

        return {
            "ranking": None,
            "errors": errors + [err],
        }

    print(
        f"\n[Agent 4 — Ranking] "
        f"Scoring candidate: "
        f"{state.get('candidate_id', '?')}"
    )

    # ── Step 1: ML scoring with fallback ─────────────────────────────────────

    try:

        features = build_feature_vector(
            evidence,
            role_fit,
            insight,
        )

        print(
            f"  [ranking] Features: {features}"
        )

        score_dict = predict_score(
            features
        )
        # ── Persist training example ─────────────────────────────

        try:
            jd = state.get(
                "job_description",
                "",
            )

            jd_hash = (
                compute_jd_hash(jd)
                if DB_AVAILABLE and jd
                else None
            )

            save_training_example(

                candidate_id=state.get(
                    "candidate_id",
                    "unknown",
                ),

                features=features,

                prediction=score_dict,

                insight=insight,
            )

            save_feature_snapshot(

                candidate_id=state.get(
                    "candidate_id",
                    "unknown",
                ),

                features=features,

                prediction=score_dict,

                insight=insight,

                jd_hash=jd_hash,
            )

        except Exception as exc:

            print(
                "[ranking_agent] "
                f"training persistence failed: {exc}"
            )
        print(
            "  [ranking] Using XGBoost scoring"
        )

    except Exception as exc:

        print(
            f"  [ranking] ML failed: {exc}"
        )

        print(
            "  [ranking] Falling back to heuristic scoring"
        )

        score_dict = compute_score(
            evidence,
            role_fit,
            insight,
        )

    print(
        f"  composite_score = "
        f"{score_dict['composite_score']}"
    )

    print(
        f"  tier            = "
        f"{score_dict['tier']}"
    )

    print(
        f"  status          = "
        f"{score_dict['status']}"
    )

    print(
        f"  rationale       = "
        f"{score_dict['rationale']}"
    )

    # ── Step 2: LLM justification ────────────────────────────────────────────

    justification, differentiator = (
        generate_justification(
            rank=1,  # single-candidate mode
            score_dict=score_dict,
            insight=insight,
            role_fit=role_fit,
        )
    )

    # ── Step 3: Build ranking output dict ────────────────────────────────────

    ranking = {

        "candidate_id": state.get(
            "candidate_id",
            "unknown",
        ),

        "github_username": state.get(
            "github_username",
            "",
        ),

        "composite_score": score_dict[
            "composite_score"
        ],

        "tier": score_dict[
            "tier"
        ],

        "status": score_dict[
            "status"
        ],

        "rank_justification": justification,

        "differentiator": differentiator,

        "components": score_dict[
            "components"
        ],

        "rationale": score_dict[
            "rationale"
        ],

        # pass-through for frontend

        "reasoning_score": score_dict[
            "components"
        ][
            "raw_reasoning_score"
        ],

        "role_fit_score": score_dict[
            "components"
        ][
            "raw_fit_score"
        ],

        "trust_score": score_dict[
            "components"
        ][
            "raw_trust_score"
        ],

        "nd_strengths_count": score_dict[
            "components"
        ][
            "nd_strengths_count"
        ],

        "recommendation": score_dict[
            "components"
        ][
            "recommendation"
        ],

        "ranked_at": datetime.utcnow().isoformat(),
    }

    # ── Step 4: Persist to DB if available ───────────────────────────────────

    if DB_AVAILABLE:

        try:

            jd = state.get(
                "job_description",
                "",
            )

            jd_hash = (
                compute_jd_hash(jd)
                if jd
                else "unknown"
            )

            candidate_id = state.get(
                "candidate_id",
                "unknown",
            )

            github = state.get(
                "github_username",
                "",
            )

            leetcode = (
                state.get(
                    "leetcode_username",
                    "",
                )
                or ""
            )

            save_score(
                jd_hash,
                candidate_id,
                github,
                leetcode,
                score_dict,
            )

            print(
                "  [DB] ranking result saved"
            )

        except Exception as exc:

            print(
                f"  [DB] save failed "
                f"(non-fatal): {exc}"
            )

    print(
        f"  [Agent 4] ✓ Done — "
        f"{score_dict['status'].upper()}"
    )

    return {
        "ranking": ranking,
        "errors": errors,
    }
