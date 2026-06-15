"""
agents/reasoning_agent/feature_engineer.py  — NEW FILE  (Phase 1)

Converts CandidateEvidence + RoleFitModel into a fixed-width FeatureVector
that the XGBoost model can consume.

WHY THIS EXISTS:
  The LLM previously received raw evidence and made its own decisions about
  what mattered. This was non-deterministic. A feature vector forces every
  decision to be grounded in the same 15 measurable numbers, always extracted
  the same way from the same inputs.

FEATURE INDEX MAP (must stay stable — changing order breaks the trained model):
  0  required_match_ratio       fraction of required skills matched (0–1)
  1  preferred_match_ratio      fraction of preferred skills matched (0–1)
  2  overall_fit_score          Agent 2 embedding fit score (0–1)
  3  github_score_norm          github_score / 100
  4  leetcode_score_norm        leetcode_score / 100 (0 if no leetcode)
  5  trust_score_norm           trust_score / 100
  6  avg_skill_confidence       mean confidence across extracted skills (0–1)
  7  skill_depth_score          production=1.0, working=0.6, exposure=0.3, avg
  8  recency_score              1 - (avg_recency_days / 365), capped 0–1
  9  commit_consistency_enc     high=1.0, medium=0.5, low=0.0
  10 project_complexity_enc     high=1.0, medium=0.5, low=0.0
  11 domain_match_ratio         domains_required ∩ domains_candidate / total_required
  12 nd_signal_count_norm       len(nd_flags) / 5  (max 5 signals)
  13 total_repos_norm           min(total_repos / 30, 1.0)
  14 has_portfolio              1.0 if portfolio_text present else 0.0
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from dataclasses import dataclass
from typing import List

import core.root  # noqa


@dataclass
class FeatureVector:
    """
    Typed wrapper around the raw numpy array.
    Carries feature names for logging and explainability.
    """
    values: np.ndarray          # shape (15,)  float32
    feature_names: List[str]
    candidate_id: str

    def as_2d(self) -> np.ndarray:
        """Returns shape (1, 15) for XGBoost prediction."""
        return self.values.reshape(1, -1)

    def to_dict(self) -> dict:
        return {
            name: round(float(val), 4)
            for name, val in zip(self.feature_names, self.values)
        }


FEATURE_NAMES = [
    "required_match_ratio",
    "preferred_match_ratio",
    "overall_fit_score",
    "github_score_norm",
    "leetcode_score_norm",
    "trust_score_norm",
    "avg_skill_confidence",
    "skill_depth_score",
    "recency_score",
    "commit_consistency_enc",
    "project_complexity_enc",
    "domain_match_ratio",
    "nd_signal_count_norm",
    "total_repos_norm",
    "has_portfolio",
]

DEPTH_MAP = {"production": 1.0, "working": 0.6, "exposure": 0.3}
CONSISTENCY_MAP = {"high": 1.0, "medium": 0.5, "low": 0.0}


def extract_features(evidence: dict, role_fit: dict, nd_inclusion: dict = None) -> FeatureVector:
    """
    Main entry point. Takes raw dicts (as they flow through LangGraph state)
    and returns a FeatureVector.

    All computations are deterministic — same inputs always produce same output.
    """
    # ── required / preferred match ratios ────────────────────────────────────
    req_skills  = role_fit.get("required_skills_matched", [])
    pref_skills = role_fit.get("preferred_skills_matched", [])

    req_matched  = sum(1 for s in req_skills  if s.get("matched", False))
    pref_matched = sum(1 for s in pref_skills if s.get("matched", False))

    req_ratio  = req_matched  / max(len(req_skills),  1)
    pref_ratio = pref_matched / max(len(pref_skills), 1)

    # ── overall fit score ─────────────────────────────────────────────────────
    overall_fit = float(role_fit.get("overall_fit_score", 0.0))

    # ── github score ──────────────────────────────────────────────────────────
    scores       = evidence.get("scores", {}) or {}
    github_norm  = (scores.get("github_score") or 0) / 100.0
    lc_raw       = scores.get("leetcode_score")
    leetcode_norm= (lc_raw / 100.0) if lc_raw is not None else 0.0

    # ── trust score ───────────────────────────────────────────────────────────
    integrity    = evidence.get("integrity", {}) or {}
    trust_norm   = (integrity.get("trust_score") or 0) / 100.0

    # ── skill confidence + depth ──────────────────────────────────────────────
    skills = evidence.get("skills", []) or []
    if skills:
        confidences   = [float(s.get("confidence", 0)) for s in skills]
        depths        = [DEPTH_MAP.get(str(s.get("depth", "")), 0.3) for s in skills]
        avg_conf      = float(np.mean(confidences))
        avg_depth     = float(np.mean(depths))
    else:
        avg_conf  = 0.0
        avg_depth = 0.0

    # ── recency score ─────────────────────────────────────────────────────────
    if skills:
        avg_recency_days = float(np.mean([s.get("recency_days", 365) for s in skills]))
        recency_score    = float(np.clip(1.0 - (avg_recency_days / 365.0), 0.0, 1.0))
    else:
        recency_score = 0.0

    # ── signals ───────────────────────────────────────────────────────────────
    signals     = evidence.get("signals", {}) or {}
    consistency = CONSISTENCY_MAP.get(signals.get("commit_consistency", "low"), 0.0)
    complexity  = CONSISTENCY_MAP.get(signals.get("project_complexity",  "low"), 0.0)
    total_repos = min((signals.get("total_repos_analyzed") or 0) / 30.0, 1.0)

    # ── domain match ratio ────────────────────────────────────────────────────
    required_domains  = set(role_fit.get("domains_required", []))
    candidate_domains = set(signals.get("domain_breadth", []))
    if required_domains:
        domain_match = len(required_domains & candidate_domains) / len(required_domains)
    else:
        domain_match = 1.0 if candidate_domains else 0.0

    # ── nd signals ────────────────────────────────────────────────────────────
    nd_norm = min(len(evidence.get("nd_flags", [])) / 5.0, 1.0)

    # ── portfolio ─────────────────────────────────────────────────────────────
    has_portfolio = 1.0 if evidence.get("portfolio_text", "").strip() else 0.0

    # ── assemble vector ───────────────────────────────────────────────────────
    values = np.array([
        req_ratio,
        pref_ratio,
        overall_fit,
        github_norm,
        leetcode_norm,
        trust_norm,
        avg_conf,
        avg_depth,
        recency_score,
        consistency,
        complexity,
        domain_match,
        nd_norm,
        total_repos,
        has_portfolio,
    ], dtype=np.float32)

    # ── ND penalty reduction (deterministic, capped at 20%) ────────────────────
    # If nd_inclusion_node detected underestimation risk, we reduce the weight
    # of the required_match_ratio feature by the computed penalty_reduction_weight.
    # This does NOT add points — it reduces unfair penalty on ND candidates.
    # The ceiling of 0.20 prevents reverse bias.
    if nd_inclusion:
        penalty_r = float(nd_inclusion.get("penalty_reduction_weight", 0.0))
        risk      = nd_inclusion.get("risk_of_underestimation", "low")
        source    = nd_inclusion.get("nd_source")
        if penalty_r > 0 and (risk in ("high", "medium") or source == "self_declared"):
            # Apply reduction to required_match_ratio (index 0) only
            # The reduction is proportional: high-risk candidates get more relief
            # but NEVER above the 0.20 hard ceiling
            adjustment = min(penalty_r, 0.20)
            original   = float(values[0])
            adjusted   = min(1.0, original + (adjustment * (1.0 - original)))
            values[0]  = np.float32(adjusted)

    return FeatureVector(
        values        = values,
        feature_names = FEATURE_NAMES,
        candidate_id  = evidence.get("candidate_id", "unknown"),
    )
