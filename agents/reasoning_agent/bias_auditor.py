from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.schemas import BiasAuditReport, HiringInsight, CandidateEvidence, RoleFitModel
from .inclusion import PROXY_FIELDS


def build_audit_report(
    evidence: CandidateEvidence,
    role_fit: RoleFitModel,
    insight: HiringInsight,
    raw_recommendation_before_nd: str,
    nd_inclusion: Optional[Dict[str, Any]] = None,   # ✅ NEW INPUT
) -> BiasAuditReport:
    """
    Build a BiasAuditReport.

    FIXED VERSION:
    - ND detection comes ONLY from nd_inclusion (single source of truth)
    - No duplicate ND detection logic
    """

    # ─────────────────────────────────────────────────────────────
    # ✅ FIX 1: Unified ND detection (CRITICAL)
    # ─────────────────────────────────────────────────────────────
    nd_inclusion = nd_inclusion or {}

    nd_detected = bool(nd_inclusion.get("nd_flag", False))
    nd_type = nd_inclusion.get("nd_type")

    # ─────────────────────────────────────────────────────────────
    # Proxies removed
    # ─────────────────────────────────────────────────────────────
    proxies_removed = sorted(PROXY_FIELDS)

    # ─────────────────────────────────────────────────────────────
    # Selection factors
    # ─────────────────────────────────────────────────────────────
    selection_factors: List[str] = []

    for s in insight.strengths:
        selection_factors.append(f"Verified skill: {s}")

    if evidence.integrity.trust_score >= 70:
        selection_factors.append(
            f"High evidence authenticity: {evidence.integrity.trust_score}/100"
        )

    if role_fit.overall_fit_score >= 0.6:
        selection_factors.append(
            f"Strong role-fit match: {role_fit.overall_fit_score:.0%}"
        )

    if getattr(evidence, "task_assessment_score", None) and evidence.task_assessment_score >= 0.7:
        selection_factors.append(
            f"Task assessment: {evidence.task_assessment_score:.0%}"
        )

    # ─────────────────────────────────────────────────────────────
    # ND uplifts
    # ─────────────────────────────────────────────────────────────
    nd_uplifts: List[str] = [
        f"{nd.signal} ({nd.weight}): {nd.evidence}"
        for nd in insight.nd_strengths
    ]

    # ─────────────────────────────────────────────────────────────
    # Risk flags
    # ─────────────────────────────────────────────────────────────
    risk_flags: List[str] = []

    if evidence.integrity.trust_score < 50:
        risk_flags.append(
            f"Low evidence authenticity ({evidence.integrity.trust_score}/100) — "
            f"review integrity flags before final decision"
        )

    for flag in evidence.integrity.flags:
        if flag.severity == "high":
            risk_flags.append(f"Integrity [{flag.flag_type}]: {flag.detail}")

    if role_fit.overall_fit_score < 0.3:
        risk_flags.append(
            "Very low embedding match — verify JD alignment before proceeding"
        )

    # ─────────────────────────────────────────────────────────────
    # Fairness score (unchanged logic — correct)
    # ─────────────────────────────────────────────────────────────
    auth_flags = sum(
        1 for f in evidence.integrity.flags if f.flag_type == "authorship_mismatch"
    )
    clone_flags = sum(
        1 for f in evidence.integrity.flags if f.flag_type == "clone_risk"
    )

    auth_deduction = min(auth_flags * 0.10, 0.20)
    clone_deduction = min(clone_flags * 0.05, 0.15)
    trust_deduction = 0.05 if evidence.integrity.trust_score < 50 else 0.0

    total_deduction = auth_deduction + clone_deduction + trust_deduction
    fairness = round(max(0.0, 1.0 - total_deduction), 2)

    # ─────────────────────────────────────────────────────────────
    # Explanation
    # ─────────────────────────────────────────────────────────────
    explanation_parts = []

    if auth_deduction > 0:
        explanation_parts.append(
            f"Authorship mismatch: -{auth_deduction:.2f} ({auth_flags} flag(s))"
        )

    if clone_deduction > 0:
        explanation_parts.append(
            f"Clone risk: -{clone_deduction:.2f} ({clone_flags} flag(s), capped)"
        )

    if trust_deduction > 0:
        explanation_parts.append(
            f"Low trust score: -{trust_deduction:.2f} (trust={evidence.integrity.trust_score}/100)"
        )

    if not explanation_parts:
        explanation_parts.append("No deductions — process fair")

    fairness_explanation = (
        f"Fairness = {fairness:.2f}. "
        + " | ".join(explanation_parts)
        + ". ND signals do NOT reduce fairness."
    )

    # ─────────────────────────────────────────────────────────────
    # RETURN
    # ─────────────────────────────────────────────────────────────
    return BiasAuditReport(
        candidate_id=evidence.candidate_id,
        generated_at=datetime.utcnow(),
        nd_signal_detected=nd_detected,     # ✅ FIXED
        proxies_removed=proxies_removed,
        fairness_score=fairness,
        fairness_explanation=fairness_explanation,
        selection_factors=selection_factors,
        risk_flags=risk_flags,
        nd_strength_uplifts=nd_uplifts,
        recommendation_before_inclusion=raw_recommendation_before_nd,
        recommendation_after_inclusion=insight.recommendation.value,
    )


# ─────────────────────────────────────────────────────────────
# EXPORT FUNCTIONS (unchanged)
# ─────────────────────────────────────────────────────────────

def export_audit_report(report: BiasAuditReport, output_dir: str = "./audit_reports") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/audit_{report.candidate_id}_{ts}.json"

    with open(filename, "w") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2, default=str)

    print(f"  [Audit] Report saved: {filename}")
    return filename


def export_audit_batch(reports: List[BiasAuditReport], output_dir: str = "./audit_reports") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/batch_audit_{ts}.json"

    batch = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_candidates": len(reports),
        "nd_detection_rate": round(
            sum(1 for r in reports if r.nd_signal_detected) / max(len(reports), 1), 2
        ),
        "avg_fairness_score": round(
            sum(r.fairness_score for r in reports) / max(len(reports), 1), 2
        ),
        "reports": [r.model_dump(mode="json") for r in reports],
    }

    with open(filename, "w") as f:
        json.dump(batch, f, indent=2, default=str)

    print(f"  [Audit] Batch report saved: {filename}")
    return filename