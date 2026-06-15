"""
agents/ranking_agent/scorer.py
Deterministic scoring — zero LLM involved.

Uses outputs from all 3 upstream agents that are already in GraphState:
  state["evidence"]  → Agent 1  (trust_score, nd_strengths)
  state["role_fit"]  → Agent 2  (overall_fit_score)
  state["insight"]   → Agent 3  (score, recommendation, skill_gaps)
"""
from __future__ import annotations

# ── Weights (must sum to 1.0) ──────────────────────────────────────────────────
W_REASONING = 0.45   # Agent 3 score  — biggest weight, already bakes in 1+2
W_ROLE_FIT  = 0.30   # Agent 2 score  — hard cosine similarity match
W_TRUST     = 0.15   # Agent 1 score  — evidence integrity
W_ND_UPLIFT = 0.10   # Agent 1 flags  — inclusion guarantee

SHORTLIST_CUTOFF = 40   # minimum score to be shortlisted

# Recommendation floors & ceilings
REC_FLOOR    = {"strong_yes": 75.0, "yes": 60.0, "maybe": 40.0, "no": 0.0}
REC_CEILING  = {"no": 39.0}   # "no" from Agent 3 → never shortlisted

ND_POINTS_PER_STRENGTH = 25.0   # 4 strengths → 100 pts in uplift component


def _gap_penalty(skill_gaps: list) -> float:
    """critical gap = -5pts, moderate = -2pts, max -20pts total."""
    penalty = 0.0
    for g in skill_gaps:
        sev = g.get("severity", "minor") if isinstance(g, dict) else "minor"
        if sev == "critical":   penalty += 5.0
        elif sev == "moderate": penalty += 2.0
    return min(penalty, 20.0)


def _nd_count(nd_strengths: list) -> int:
    """high_signal = 1 point, medium_signal = 0.5 point each."""
    count = 0.0
    for nd in nd_strengths:
        w = nd.get("weight", "") if isinstance(nd, dict) else ""
        count += 1.0 if w == "high_signal" else 0.5
    return int(round(count))


def compute_score(evidence: dict, role_fit: dict, insight: dict) -> dict:
    """
    Returns a score dict:
    {
        composite_score: float,      # 0-100 final score
        tier: str,                   # elite / strong / qualified / borderline / below_bar
        status: str,                 # shortlisted / rejected
        components: dict,            # breakdown of each sub-score
        rationale: str               # one-sentence plain English
    }
    """
    # ── Pull values from each agent ────────────────────────────────────────────
    integrity   = evidence.get("integrity") or {}
    trust_score = float(integrity.get("trust_score", 50) if isinstance(integrity, dict) else 50)

    nd_strengths    = insight.get("nd_strengths") or []
    nd_count        = _nd_count(nd_strengths)
    nd_uplift_raw   = min(nd_count * ND_POINTS_PER_STRENGTH, 100.0)

    fit_score       = float(role_fit.get("overall_fit_score", 0.0)) * 100.0   # 0-1 → 0-100
    reasoning_score = float(insight.get("score", 0))
    recommendation  = str(insight.get("recommendation", "no")).lower()
    skill_gaps      = insight.get("skill_gaps") or []
    gap_pen         = _gap_penalty(skill_gaps)

    # ── Weighted formula ───────────────────────────────────────────────────────
    raw = (
        reasoning_score * W_REASONING
        + fit_score     * W_ROLE_FIT
        + trust_score   * W_TRUST
        + nd_uplift_raw * W_ND_UPLIFT
        - gap_pen
    )

    # ── Apply recommendation floor / ceiling ───────────────────────────────────
    floor   = REC_FLOOR.get(recommendation, 0.0)
    ceiling = REC_CEILING.get(recommendation, 100.0)
    composite = round(max(0.0, min(100.0, max(floor, min(ceiling, raw)))), 2)

    # ── Tier ──────────────────────────────────────────────────────────────────
    if   composite >= 85: tier = "elite"
    elif composite >= 70: tier = "strong"
    elif composite >= 55: tier = "qualified"
    elif composite >= SHORTLIST_CUTOFF: tier = "borderline"
    else:                 tier = "below_bar"

    status = "shortlisted" if composite >= SHORTLIST_CUTOFF else "rejected"

    rationale = (
        f"Composite {composite}/100 — "
        f"reasoning {int(reasoning_score)}, "
        f"role fit {fit_score:.0f}%, "
        f"trust {int(trust_score)}"
        + (f", ND uplift ({nd_count} signal(s))" if nd_count else "")
        + (f", gap penalty -{gap_pen:.0f}pts" if gap_pen else "")
        + f". Recommendation: {recommendation}."
    )

    return {
        "composite_score": composite,
        "tier":            tier,
        "status":          status,
        "rationale":       rationale,
        "components": {
            "reasoning_component":  round(reasoning_score * W_REASONING, 2),
            "role_fit_component":   round(fit_score       * W_ROLE_FIT,  2),
            "trust_component":      round(trust_score     * W_TRUST,     2),
            "nd_uplift_component":  round(nd_uplift_raw   * W_ND_UPLIFT, 2),
            "gap_penalty":          round(gap_pen, 2),
            "raw_reasoning_score":  int(reasoning_score),
            "raw_fit_score":        round(fit_score, 2),
            "raw_trust_score":      int(trust_score),
            "nd_strengths_count":   nd_count,
            "recommendation":       recommendation,
        }
    }
