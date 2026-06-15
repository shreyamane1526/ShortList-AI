"""
agents/reasoning_agent/nd_inclusion_node.py  — NEW FILE

POSITION IN PIPELINE:
  evidence → context → [nd_inclusion] → reasoning → ranking → feedback

This node runs AFTER Agent 2 (we have role_fit) and BEFORE Agent 3
(before the ML decision is made). It:

  1. Calls nd_strength_mapper → detects ND strength signals from full evidence
  2. Detects underestimation risk → flags which metrics are distorted
  3. Computes penalty_reduction_weight → passed to feature_engineer
  4. Generates recommended_action → drives task adaptation
  5. Writes NDInclusionReport to HiringState.nd_inclusion

The reasoning agent reads nd_inclusion and adjusts its feature vector
BEFORE calling XGBoost. This keeps determinism intact — the adjustment
is computed once, documented, and reproducible.

OUTPUT SCHEMA (also in core/schemas.py):
{
  "nd_flag": bool,
  "nd_type": "adhd|dyslexia|autism|mixed|none",
  "strengths_detected": [...],
  "risk_of_underestimation": "low|medium|high",
  "recommended_action": "proceed|review|alt_task",
  "penalty_reduction_weight": 0.0-0.20,
  "task_format": "standard|adhd|dyslexia|autism",
  "nd_summary": "neutral plain-English summary for LLM"
}
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core.root  # noqa

from dataclasses import asdict
from typing import Optional

from core.schemas import HiringState, CandidateEvidence, RoleFitModel
from .nd_strength_mapper import map_nd_strengths, NDMappingResult


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic rules
# ══════════════════════════════════════════════════════════════════════════════

def _classify_nd_type(result: NDMappingResult) -> str:
    """
    Classifies the dominant ND trait cluster from signal evidence.
    Returns "none" when no signals detected.
    Returns "mixed" when 2+ clusters have equal weight.
    """
    if not result.signals:
        return "none"

    cluster_weights: dict = {}
    for s in result.signals:
        w = 2 if s.weight == "high_signal" else 1
        cluster_weights[s.trait_cluster] = cluster_weights.get(s.trait_cluster, 0) + w

    if not cluster_weights:
        return "none"

    max_weight = max(cluster_weights.values())
    top_clusters = [c for c, w in cluster_weights.items() if w == max_weight]

    if len(top_clusters) > 1:
        return "mixed"
    return top_clusters[0]


def _assess_underestimation_risk(result: NDMappingResult, req_ratio: float) -> str:
    """
    Deterministic three-level risk assessment.

    HIGH:   strong ND signals + underestimation risks present + req_ratio < 0.40
    MEDIUM: ND signals present + (risks present OR req_ratio < 0.55)
    LOW:    ND signals present but no significant metric distortion detected
    """
    has_high_signals = any(s.weight == "high_signal" for s in result.signals)
    has_high_risks   = any(r.severity == "high" for r in result.underestimation_risks)
    has_any_risks    = bool(result.underestimation_risks)

    if not result.signals:
        return "low"

    if has_high_signals and has_high_risks and req_ratio < 0.40:
        return "high"
    elif result.signals and (has_any_risks or req_ratio < 0.55):
        return "medium"
    else:
        return "low"


def _recommend_action(risk_level: str, nd_type: str, req_ratio: float) -> str:
    """
    Deterministic recommended action.

    proceed:  standard pipeline — ND strengths noted but no intervention needed
    review:   flag for human recruiter review before final decision
    alt_task: generate an ND-adapted work sample (nd_task_generator)

    Rules:
      HIGH risk + req_ratio < 0.35  → alt_task (candidate likely undervalued by metrics)
      HIGH risk + req_ratio 0.35-0.5 → review
      MEDIUM risk                   → review
      LOW risk                      → proceed
    """
    if risk_level == "high" and req_ratio < 0.35:
        return "alt_task"
    elif risk_level == "high":
        return "review"
    elif risk_level == "medium":
        return "review"
    else:
        return "proceed"


def _resolve_task_format(nd_type: str, recommended_action: str) -> str:
    """
    Maps ND type to task presentation format.
    Only relevant when recommended_action == "alt_task".
    """
    if recommended_action != "alt_task":
        return "standard"
    mapping = {
        "adhd":    "adhd",
        "dyslexia": "dyslexia",
        "autism":  "autism",
        "mixed":   "adhd",    # ADHD format is most universally accessible
        "none":    "standard",
    }
    return mapping.get(nd_type, "standard")


def _normalize_self_declared_type(nd_type: Optional[str]) -> Optional[str]:
    if not nd_type:
        return None
    value = str(nd_type).strip().lower()
    allowed = {"adhd", "dyslexia", "autism", "other"}
    return value if value in allowed else "other"


# ══════════════════════════════════════════════════════════════════════════════
# LangGraph node
# ══════════════════════════════════════════════════════════════════════════════

def nd_inclusion_node(state: dict) -> dict:
    """
    Reads:  evidence + role_fit from HiringState
    Writes: nd_inclusion (NDInclusionReport dict) to HiringState

    Runs deterministically. No LLM call here — pure signal processing.
    """
    hiring_state = HiringState(**state)

    # Guard: skip if agents 1 or 2 failed
    if hiring_state.evidence is None or hiring_state.role_fit is None:
        print("[ND Inclusion] Skipping — evidence or role_fit missing")
        return {"nd_inclusion": None, "errors": hiring_state.errors}

    evidence = (hiring_state.evidence if isinstance(hiring_state.evidence, dict)
                else hiring_state.evidence.model_dump())
    role_fit = (hiring_state.role_fit if isinstance(hiring_state.role_fit, dict)
                else hiring_state.role_fit.model_dump())

    print(f"\n[ND Inclusion] Candidate: {evidence.get('candidate_id', 'unknown')}")

    # Compute required_match_ratio for risk assessment
    req_skills  = role_fit.get("required_skills_matched", [])
    req_matched = sum(1 for s in req_skills if s.get("matched", False))
    req_ratio   = req_matched / max(len(req_skills), 1)

    # Run ND strength mapping
    result = map_nd_strengths(
        evidence        = evidence,
        role_fit        = role_fit,
        leetcode_data   = {},   # raw LC data not in state — signals inferred from scores
        task_assessment = {
            "score":  evidence.get("task_assessment_score"),
            "domain": evidence.get("task_assessment_domain"),
        },
    )

    self_declared = state.get("candidate_nd_self_id") or {}
    self_declared_nd = self_declared.get("neurodivergent") is True

    # Candidate self-declaration has priority for the support flag. Behavioral
    # signals remain useful as neutral strengths and underestimation evidence.
    source        = "self_declared" if self_declared_nd else "inferred"
    inferred_type = _classify_nd_type(result)
    nd_type       = (
        _normalize_self_declared_type(self_declared.get("nd_type"))
        or inferred_type
        if self_declared_nd
        else inferred_type
    )
    risk_level    = _assess_underestimation_risk(result, req_ratio)
    action        = _recommend_action(risk_level, nd_type, req_ratio)
    task_format   = _resolve_task_format(nd_type, action)
    nd_flag       = self_declared_nd or bool(result.signals)
    penalty_weight = result.penalty_reduction_weight
    nd_score       = result.nd_score
    nd_summary     = result.summary

    if self_declared_nd:
        penalty_weight = max(penalty_weight, 0.05)
        nd_score = max(nd_score, 0.25)
        nd_summary = (
            "Candidate opted into neurodiversity support. Use this only to "
            "reduce evaluation underestimation and provide accessible feedback."
        )

    # Build output report
    nd_inclusion = {
        "nd_flag":                  nd_flag,
        "nd_type":                  nd_type,
        "nd_source":                source,
        "strengths_detected":       [
            {
                "signal":         s.signal_name,
                "trait_cluster":  s.trait_cluster,
                "strength_label": s.strength_label,
                "evidence":       s.evidence,
                "weight":         s.weight,
            }
            for s in result.signals
        ],
        "underestimation_risks": [
            {
                "risk_factor":      r.risk_factor,
                "description":      r.description,
                "affected_metric":  r.affected_metric,
                "severity":         r.severity,
            }
            for r in result.underestimation_risks
        ],
        "risk_of_underestimation":  risk_level,
        "recommended_action":       action,
        "penalty_reduction_weight": penalty_weight,
        "nd_score":                 nd_score,
        "task_format":              task_format,
        "nd_summary":               nd_summary,
        "dominant_trait_cluster":   result.dominant_trait_cluster,
    }

    print(f"  ND flag          : {nd_inclusion['nd_flag']}")
    print(f"  ND type          : {nd_type}")
    print(f"  ND source        : {source}")
    print(f"  Strengths found  : {len(result.signals)}")
    print(f"  Underest. risk   : {risk_level}")
    print(f"  Recommended      : {action}")
    print(f"  Penalty reduction: {result.penalty_reduction_weight:.0%}")
    if action == "alt_task":
        print(f"  Task format      : {task_format}")

    return {"nd_inclusion": nd_inclusion}
