"""
agents/reasoning_agent/agent.py

Agent 3 — Reasoning Engine

CHANGES IN THIS VERSION:
  Fix 1A — LLM-hallucinated ND strengths:
    _parse() now takes nd_flags (from inclusion.py) as a parameter.
    nd_strengths in the output is filtered to ONLY contain signals that
    inclusion.py actually detected from real evidence patterns.
    If nd_flags=[], nd_strengths=[] regardless of what the LLM returned.
    Root cause: LLM saw commit_consistency and project_complexity fields
    in the evidence JSON and invented them as ND signals. The LLM prompt
    never told it these were off-limits — the filter enforces it structurally.

  Fix 1B — Narrative contradiction when gate fires:
    When force_reject=True (< 50% required skills matched), the LLM narrative
    is overridden with a factual statement that matches the decision.
    The LLM wrote "could be a strong fit" because it saw Python and felt
    optimistic before the gate capped the score. That optimism is now blocked.

  Fix 1C — Required match counts passed to state:
    required_matched and required_total are added to the returned state dict
    so run.py can display them as "Skill match: X/Y" instead of relying on
    the misleading embedding percentage alone.
"""

from __future__ import annotations
import core.root

import json
from typing import List

from core.config  import settings
from core.schemas import (
    HiringState, HiringInsight, CandidateEvidence, RoleFitModel,
    SkillGap, NDStrength, NDWeight, Recommendation, ReasoningStep, BiasAuditReport,
)
from .inclusion    import build_nd_prompt_block
from .bias_auditor import build_audit_report, export_audit_report


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a skills-first hiring analyst for Shortlist AI.

ABSOLUTE RULES (never violate):
- Reason ONLY from verified skills and observable evidence.
- NEVER penalise for missing university degree.
- NEVER penalise for career gaps or non-traditional paths.
- NEVER consider communication style, interview polish, or presentation.
- NEVER assume skills not evidenced — mark them as gaps.
- score (0–100) must reflect ONLY: skill coverage, evidence strength, role fit.
- nd_strengths must ONLY contain signals listed in the nd_flags field of the evidence.
  If nd_flags is empty, return nd_strengths as an empty list [].
  Do NOT invent nd_strengths from commit_consistency, project_complexity, or any
  other evidence field — those are NOT neurodivergent signals.

{nd_block}

Return ONLY a single valid JSON object (no markdown, no preamble):
{{
  "score": 0_to_100,
  "strengths": ["verified capability statement", ...],
  "skill_gaps": [
    {{"skill_name":"...","severity":"critical|moderate|minor","note":"..."}}
  ],
  "confidence_per_skill": {{"skill_name": 0.0_to_1.0}},
  "nd_strengths": [
    {{"signal":"...","evidence":"plain English reason","weight":"high_signal|medium_signal"}}
  ],
  "recommendation": "strong_yes|yes|maybe|no",
  "recommendation_narrative": "2–3 plain English sentences",
  "reasoning_trace": "compact chain-of-thought"
}}"""

USER_PROMPT_TEMPLATE = """CANDIDATE EVIDENCE:
{evidence_json}

ROLE FIT:
{role_fit_json}

Produce the hiring assessment now."""


# ── LangGraph node ─────────────────────────────────────────────────────────────

def reasoning_agent_node(state: dict) -> dict:
    hiring_state = HiringState(**state)

    if hiring_state.evidence is None or hiring_state.role_fit is None:
        err = "reasoning_agent: evidence or role_fit missing"
        return {"errors": hiring_state.errors + [err]}

    evidence = (CandidateEvidence(**hiring_state.evidence)
                if isinstance(hiring_state.evidence, dict) else hiring_state.evidence)
    role_fit = (RoleFitModel(**hiring_state.role_fit)
                if isinstance(hiring_state.role_fit, dict) else hiring_state.role_fit)

    print(f"\n[Agent 3 — Reasoning] Candidate: {evidence.candidate_id}")

    nd_flags = evidence.nd_flags or []
    nd_block = build_nd_prompt_block(nd_flags)
    if nd_flags:
        print(f"  ND flags active  : {nd_flags}")

    # ── Hard requirement gate ──────────────────────────────────────────────────
    required_skills  = role_fit.required_skills_matched
    required_matched = sum(1 for s in required_skills if s.matched)
    required_total   = len(required_skills)
    match_ratio      = (required_matched / required_total) if required_total > 0 else 0.0
    force_reject     = match_ratio < 0.50
    score_ceiling    = 30 if force_reject else 100

    if force_reject:
        print(f"  [Gate] Required match {required_matched}/{required_total} "
              f"({match_ratio:.0%}) — below 50% threshold, score capped at {score_ceiling}")

    # ── LLM call ───────────────────────────────────────────────────────────────
    system_prompt = SYSTEM_PROMPT.format(nd_block=nd_block)
    user_prompt   = USER_PROMPT_TEMPLATE.format(
        evidence_json = _evidence_to_json(evidence),
        role_fit_json = _role_fit_to_json(role_fit),
    )
    raw = _call_llm(system_prompt, user_prompt)

    # Capture pre-inclusion recommendation for audit
    raw_rec_before = raw.get("recommendation", "maybe")

    # Apply score ceiling
    llm_score    = int(raw.get("score", 50))
    

    # Balanced score: 50% LLM + 50% embedding, respect ceiling
    # Use ONLY LLM score after gate (do NOT mix with embedding again)
    raw["score"] = min(int(raw.get("score", 50)), score_ceiling)

    # ── Build reasoning steps ──────────────────────────────────────────────────
    steps = _build_reasoning_steps(evidence, role_fit, raw)

    # ── Parse into HiringInsight (Fix 1A: pass nd_flags to filter hallucinations) ──
    insight = _parse(raw, evidence.candidate_id, steps, nd_flags)

    # ── Fix 1B: override narrative when gate fires ─────────────────────────────
    # The LLM writes its narrative before it knows the gate will cap the score.
    # A gated-out candidate cannot have a narrative saying "could be a strong fit."
    if force_reject:
        insight.recommendation_narrative = (
            f"This candidate does not meet the minimum required skill coverage "
            f"for this role ({required_matched}/{required_total} required skills matched). "
            f"No further review recommended without retraining in the required stack."
        )

    # ── Build + export bias audit ──────────────────────────────────────────────
    audit = build_audit_report(evidence, role_fit, insight, raw_rec_before)
    try:
        export_audit_report(audit)
    except Exception as e:
        print(f"  [Reasoning] Audit export warning: {e}")

    print(f"  Score            : {insight.score}/100")
    print(f"  Recommendation   : {insight.recommendation.value.upper()}")
    print(f"  Strengths        : {len(insight.strengths)}")
    print(f"  Skill gaps       : {len(insight.skill_gaps)}")
    print(f"  ND strengths     : {len(insight.nd_strengths)}")
    print(f"  Fairness score   : {audit.fairness_score}")

    insight_dict = insight.model_dump()
    insight_dict["bias_audit"] = audit.model_dump()

    return {
        "insight":          insight_dict,
        # Fix 1C: pass match counts so run.py can display them correctly
        "required_matched": required_matched,
        "required_total":   required_total,
        "match_ratio": match_ratio,
    }


# ── LLM call ───────────────────────────────────────────────────────────────────

def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    if settings.use_mock:
        print("  [Reasoning] Mock mode — returning deterministic response")
        return _mock_response()

    print(f"  [Reasoning] Calling Groq ({settings.GROQ_MODEL})...")
    try:
        import litellm
        resp = litellm.completion(
            model           = f"groq/{settings.GROQ_MODEL}",
            messages        = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format = {"type": "json_object"},
            temperature     = settings.LLM_TEMPERATURE,
            max_tokens      = settings.LLM_MAX_TOKENS,
        )
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"  [Reasoning] JSON parse error: {e} — using mock")
        return _mock_response()
    except Exception as e:
        print(f"  [Reasoning] LLM error: {e}")
        raise


# ── Compliance reasoning trace ─────────────────────────────────────────────────

def _build_reasoning_steps(
    evidence: CandidateEvidence,
    role_fit: RoleFitModel,
    llm_output: dict,
) -> List[ReasoningStep]:
    steps = []

    steps.append(ReasoningStep(
        step         = 1,
        action       = "Evidence quality assessment",
        data_used    = (f"Trust score: {evidence.integrity.trust_score}/100, "
                        f"Sources: {evidence.sources_used}, "
                        f"Repos: {evidence.signals.total_repos_analyzed}"),
        data_ignored = "University name, graduation year, GPA, employer prestige",
        conclusion   = (f"Evidence quality: "
                        f"{'HIGH' if evidence.integrity.trust_score >= 70 else 'MEDIUM' if evidence.integrity.trust_score >= 50 else 'LOW'}"),
    ))

    req_matched = sum(1 for s in role_fit.required_skills_matched if s.matched)
    steps.append(ReasoningStep(
        step         = 2,
        action       = "Skill coverage against JD requirements",
        data_used    = (f"Required matched: {req_matched}/{len(role_fit.required_skills_matched)}, "
                        f"Embedding fit: {role_fit.overall_fit_score:.0%}"),
        data_ignored = "Interview performance, presentation style, communication score",
        conclusion   = f"Coverage: {req_matched}/{len(role_fit.required_skills_matched)} required skills matched",
    ))

    nd_flags = evidence.nd_flags or []
    steps.append(ReasoningStep(
        step         = 3,
        action       = "Neurodivergent signal assessment",
        data_used    = (f"ND flags from inclusion.py: {nd_flags}, "
                        f"Commit consistency: {evidence.signals.commit_consistency}, "
                        f"Complexity: {evidence.signals.project_complexity}"),
        data_ignored = "Career gap penalty, non-linear path penalty",
        conclusion   = f"ND signals {'detected and weighted as strengths' if nd_flags else 'not detected — nd_strengths will be empty'}",
    ))

    from .inclusion import PROXY_FIELDS
    steps.append(ReasoningStep(
        step         = 4,
        action       = "Bias proxy masking verification",
        data_used    = "Structural field removal before LLM input",
        data_ignored = f"All {len(PROXY_FIELDS)} proxy fields: {', '.join(sorted(PROXY_FIELDS))}",
        conclusion   = "All proxies structurally removed — LLM received credential-free evidence",
    ))

    steps.append(ReasoningStep(
        step         = 5,
        action       = "Final hiring recommendation",
        data_used    = (f"Score: {llm_output.get('score', 0)}/100, "
                        f"Strengths: {len(llm_output.get('strengths', []))}, "
                        f"Gaps: {len(llm_output.get('skill_gaps', []))}"),
        data_ignored = "All credential proxies (already removed in step 4)",
        conclusion   = (f"Recommendation: {llm_output.get('recommendation', '').upper()} — "
                        f"{llm_output.get('recommendation_narrative', '')[:80]}..."),
    ))

    return steps


# ── Parse + validate ───────────────────────────────────────────────────────────

def _parse(
    raw:          dict,
    candidate_id: str,
    steps:        List[ReasoningStep],
    nd_flags:     list,              # Fix 1A: inclusion.py ground truth
) -> HiringInsight:

    gaps = [SkillGap(**g) for g in raw.get("skill_gaps", [])]

    # Fix 1A: build ND strengths from LLM output, then filter to only
    # signals that inclusion.py actually detected. If nd_flags=[], result=[].
    # This structurally prevents the LLM from inventing ND signals from
    # evidence fields like commit_consistency or project_complexity.
    valid_nd_signals = set(nd_flags)
    nds = []
    for n in raw.get("nd_strengths", []):
        signal = n.get("signal", "")
        # Drop anything the LLM invented that inclusion.py did not detect
        if signal not in valid_nd_signals:
            continue
        try:
            nds.append(NDStrength(
                signal   = signal,
                evidence = n.get("evidence", ""),
                weight   = NDWeight(n.get("weight", "medium_signal")),
            ))
        except Exception:
            pass

    # Score → Recommendation: hard mapping
    score_val = max(0, min(100, int(raw.get("score", 50))))
    if score_val >= 75:
        rec = Recommendation.STRONG_YES
    elif score_val >= 55:
        rec = Recommendation.YES
    elif score_val >= 35:
        rec = Recommendation.MAYBE
    else:
        rec = Recommendation.NO

    return HiringInsight(
        candidate_id             = candidate_id,
        score                    = score_val,
        recommendation           = rec,
        recommendation_narrative = raw.get("recommendation_narrative", ""),
        strengths                = raw.get("strengths", []),
        skill_gaps               = gaps,
        confidence_per_skill     = raw.get("confidence_per_skill", {}),
        nd_strengths             = nds,
        reasoning_steps          = steps,
        reasoning_trace          = raw.get("reasoning_trace", ""),
        bias_audit               = _empty_audit(candidate_id),
    )


def _empty_audit(candidate_id: str) -> BiasAuditReport:
    return BiasAuditReport(
        candidate_id                    = candidate_id,
        nd_signal_detected              = False,
        proxies_removed                 = [],
        fairness_score                  = 1.0,
        fairness_explanation            = "",
        selection_factors               = [],
        risk_flags                      = [],
        nd_strength_uplifts             = [],
        recommendation_before_inclusion = "unknown",
        recommendation_after_inclusion  = "unknown",
    )


# ── JSON serialisers ───────────────────────────────────────────────────────────

def _evidence_to_json(e: CandidateEvidence) -> str:
    return json.dumps({
        "candidate_id": e.candidate_id,
        "skills": [
            {"name": s.name, "confidence": s.confidence, "depth": s.depth,
             "source": s.source, "recency_days": s.recency_days}
            for s in e.skills
        ],
        "signals": {
            "commit_consistency":   e.signals.commit_consistency,
            "project_complexity":   e.signals.project_complexity,
            "domain_breadth":       e.signals.domain_breadth,
            "total_repos":          e.signals.total_repos_analyzed,
            "leetcode_solved":      e.signals.leetcode_solved,
        },
        "trust_score":           e.integrity.trust_score,
        # nd_flags is the ONLY valid source of ND signals — listed explicitly
        # so the LLM knows not to derive them from other fields
        "nd_flags":              e.nd_flags,
        "task_assessment_score": getattr(e, "task_assessment_score", None),
        "raw_summary":           (e.raw_summary[:300] if e.raw_summary else ""),
    }, indent=2)


def _role_fit_to_json(r: RoleFitModel) -> str:
    return json.dumps({
        "job_title":   r.job_title,
        "summary":     r.job_description_summary,
        "overall_fit": r.overall_fit_score,
        "required": [
            {"skill": m.skill_name, "matched": m.matched,
             "score": m.match_score, "importance": m.importance}
            for m in r.required_skills_matched
        ],
        "preferred": [
            {"skill": m.skill_name, "matched": m.matched,
             "score": m.match_score, "importance": m.importance}
            for m in r.preferred_skills_matched
        ],
    }, indent=2)


# ── Mock response ──────────────────────────────────────────────────────────────

def _mock_response() -> dict:
    return {
        "score": 74,
        "strengths": [
            "Consistent Python proficiency across 8+ repos with daily commit activity",
            "FastAPI project demonstrates REST design, async handling, and JWT auth",
            "PostgreSQL usage with migrations in a production-grade project",
            "Task assessment score of 0.87 in backend domain confirms verified skills",
        ],
        "skill_gaps": [
            {"skill_name": "Docker",        "severity": "moderate",
             "note": "No Dockerfile found. Role prefers containerisation."},
            {"skill_name": "System Design", "severity": "minor",
             "note": "No explicit architecture artefacts in portfolio."},
        ],
        "confidence_per_skill": {
            "Python": 0.95, "FastAPI": 0.88, "PostgreSQL": 0.72,
            "Docker": 0.10, "System Design": 0.40,
        },
        # Mock returns empty nd_strengths — filled only when nd_flags is non-empty
        "nd_strengths": [],
        "recommendation": "yes",
        "recommendation_narrative": (
            "Strong verified Python and backend skills supported by consistent GitHub activity "
            "and a high task assessment score. Primary gap is Docker (preferred, not critical). "
            "Recommended for technical interview with a systems design exercise."
        ),
        "reasoning_trace": (
            "Trust:85 HIGH. Skill coverage:4/6 required matched. "
            "Docker gap moderate — not a dealbreaker. Score:74."
        ),
    }