"""
agents/feedback_agent/agent.py  —  Agent 5

Feedback Agent — takes all four upstream agent outputs and produces a rich,
structured feedback JSON object.

Output schema:
  {
    "why_not_selected":          { reasons, tone, improvement_hints }
    "improvement_plan":          { short_term, long_term }
    "learning_path":             [ { week, topic, resources } ]
    "skill_match_visualization": { required_skills, matched, missing, partial }
    "confidence_score":          { score, level, factors }
    "badges":                    [ "🏆 Top Candidate", ... ]
    "candidate_report_markdown": "## Evaluation Summary\n..."
    "recruiter_summary":         "This candidate is strong in..."
  }

LLM (Groq) generates the narrative sections; deterministic logic handles
skill_match_visualization, confidence_score, and badges.
Falls back to template-based generation if the LLM call fails.
"""
from __future__ import annotations
from .scoring.confidence import (
    compute_confidence_score,
)
import json
import logging
from typing import Any
from .resources.retriever import (
    retrieve_learning_resources,
)

from .generators.roadmap_generator import (
    generate_learning_roadmap,
)
from core.config import settings

logger = logging.getLogger(__name__)


# ── Groq client (lazy init) ────────────────────────────────────────────────────

def _groq_client():
    from groq import Groq  # type: ignore
    return Groq(api_key=settings.GROQ_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# Public LangGraph node
# ═══════════════════════════════════════════════════════════════════════════════

def feedback_agent_node(state: dict) -> dict:
    """
    LangGraph node — Agent 5.

    Reads:  state["evidence"], state["role_fit"], state["insight"], state["ranking"]
    Writes: state["feedback_report"]
    """
    errors: list = list(state.get("errors", []))

    evidence = state.get("evidence") or {}
    role_fit = state.get("role_fit") or {}
    insight  = state.get("insight")  or {}
    ranking  = state.get("ranking")  or {}

    if not insight:
        err = "feedback_agent: no insight in state — Agent 3 must run first"
        logger.warning(err)
        return {"feedback_report": None, "errors": errors + [err]}

    print(f"\n[Agent 5 — Feedback] Candidate: {state.get('candidate_id', '?')}")

    try:
        report = feedback_agent_run(evidence, role_fit, insight, ranking)
        print(f"  Confidence score : {report['confidence_score']['score']}")
        print(f"  Badges           : {report['badges']}")
        return {"feedback_report": report, "errors": errors}
    except Exception as exc:
        err = f"feedback_agent: {exc}"
        logger.error(err)
        return {"feedback_report": None, "errors": errors + [err]}


# ═══════════════════════════════════════════════════════════════════════════════
# Core function — callable directly (not just as a LangGraph node)
# ═══════════════════════════════════════════════════════════════════════════════

def feedback_agent_run(
    evidence: dict,
    role_fit: dict,
    insight: dict,
    ranking: dict,
) -> dict[str, Any]:
    """
    Build the full feedback JSON from the four upstream agent outputs.

    Args:
        evidence : Agent 1 output dict (CandidateEvidence.model_dump())
        role_fit : Agent 2 output dict (RoleFitModel.model_dump())
        insight  : Agent 3 output dict (HiringInsight.model_dump())
        ranking  : Agent 4 output dict

    Returns:
        Structured feedback dict matching the required JSON schema.
    """
    # ── 1. Deterministic sections (no LLM) ────────────────────────────────────
    skill_viz    = _build_skill_match_visualization(role_fit)
    confidence   = compute_confidence_score(evidence, insight, role_fit)
    badges       = _assign_badges(ranking, evidence)

    # ── 2. LLM sections (Groq, with template fallback) ────────────────────────
    llm_sections = _generate_llm_sections(
        evidence,
        role_fit,
        insight,
        ranking,
        skill_viz,
    )

    # ── 3. Learning roadmap generation ────────────────────────────────────────

    skill_gaps = insight.get(
        "skill_gaps",
        [],
    )

    learning_resources = (
        retrieve_learning_resources(
            skill_gaps
        )
    )

    learning_roadmap = (
        generate_learning_roadmap(
            skill_gaps=skill_gaps,
            learning_resources=learning_resources,
            accessibility_mode="standard",
        )
    )

    return {
        "why_not_selected":          llm_sections["why_not_selected"],
        "improvement_plan":          llm_sections["improvement_plan"],
        "learning_path":             llm_sections["learning_path"],
        "learning_roadmap":          learning_roadmap,
        "skill_match_visualization": skill_viz,
        "confidence_score":          confidence,
        "badges":                    badges,
        "candidate_report_markdown": llm_sections["candidate_report_markdown"],
        "recruiter_summary":         llm_sections["recruiter_summary"],
    }
# ═══════════════════════════════════════════════════════════════════════════════
# Deterministic helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _build_skill_match_visualization(role_fit: dict) -> dict:
    """
    Derive required_skills, matched, missing, partial directly from Agent 2 output.
    'partial' = required skill with 0.3 ≤ match_score < threshold (not fully matched).
    """
    required_skills: list[str] = []
    matched:  list[str] = []
    missing:  list[str] = []
    partial:  list[str] = []

    PARTIAL_FLOOR = 0.30   # below this → missing; above but not matched → partial

    for sm in role_fit.get("required_skills_matched", []):
        name  = sm.get("skill_name", "")
        score = float(sm.get("match_score", 0.0))
        is_matched = bool(sm.get("matched", False))

        required_skills.append(name)
        if is_matched:
            matched.append(name)
        elif score >= PARTIAL_FLOOR:
            partial.append(name)
        else:
            missing.append(name)

    # Also surface preferred skills that were matched
    for sm in role_fit.get("preferred_skills_matched", []):
        if sm.get("matched"):
            name = sm.get("skill_name", "")
            if name and name not in matched:
                matched.append(name)

    return {
        "required_skills": required_skills,
        "matched":         matched,
        "missing":         missing,
        "partial":         partial,
    }


def _compute_confidence_score(evidence: dict, insight: dict, role_fit: dict) -> dict:
    """
    confidence = trust_score * 0.3 + fairness_score * 0.2 + overall_fit * 0.5

    Maps to:
      Low    < 40
      Medium 40 – 70
      High   > 70
    """
    integrity     = evidence.get("integrity") or {}
    trust_score   = float(integrity.get("trust_score", 50) if isinstance(integrity, dict) else 50)
    overall_fit   = float(role_fit.get("overall_fit_score", 0.5)) * 100   # 0-1 → 0-100

    bias_audit    = insight.get("bias_audit") or {}
    fairness_raw  = bias_audit.get("fairness_score", 0.7) if isinstance(bias_audit, dict) else 0.7
    fairness_score = float(fairness_raw) * 100   # 0-1 → 0-100

    score = round(trust_score * 0.3 + fairness_score * 0.2 + overall_fit * 0.5)
    score = max(0, min(100, score))

    if score > 70:
        level = "High"
    elif score >= 40:
        level = "Medium"
    else:
        level = "Low"

    # Build human-readable factors
    factors: list[str] = []
    signals = evidence.get("signals") or {}
    if isinstance(signals, dict):
        cc = signals.get("commit_consistency", "")
        if cc == "high":
            factors.append("GitHub activity high")
        elif cc == "low":
            factors.append("GitHub activity low")

    if trust_score >= 75:
        factors.append("Strong evidence integrity")
    elif trust_score < 50:
        factors.append("Evidence integrity concerns")

    skill_viz_matched = len([
        sm for sm in (role_fit.get("required_skills_matched") or [])
        if sm.get("matched")
    ])
    skill_viz_total = len(role_fit.get("required_skills_matched") or [])
    if skill_viz_total:
        if skill_viz_matched / skill_viz_total >= 0.7:
            factors.append("Strong skill coverage")
        else:
            factors.append("Resume skills incomplete")

    if not factors:
        factors.append("Based on available evidence")

    return {"score": score, "level": level, "factors": factors}


def _assign_badges(ranking: dict, evidence: dict) -> list[str]:
    """
    🏆 Top Candidate   — composite_score > 80
    🔥 High Potential  — composite_score > 60 AND tier in [elite, strong, qualified, potential]
    ⚡ Fast Learner    — many skills but low account age (proxy for rapid growth)
    """
    badges: list[str] = []
    composite = float(ranking.get("composite_score") or 0)
    tier       = (ranking.get("tier") or "").lower()

    if composite > 80:
        badges.append("🏆 Top Candidate")

    if composite > 60 and tier in ("elite", "strong", "qualified", "potential"):
        badges.append("🔥 High Potential")

    # Fast Learner: many skills relative to account age
    skills = evidence.get("skills") or []
    signals = evidence.get("signals") or {}
    account_age = None
    if isinstance(signals, dict):
        account_age = signals.get("account_age_days")

    if len(skills) >= 8 and account_age is not None and account_age < 730:
        badges.append("⚡ Fast Learner")
    elif len(skills) >= 12:
        # Many skills even without age data → likely fast learner
        badges.append("⚡ Fast Learner")

    return badges


# ═══════════════════════════════════════════════════════════════════════════════
# LLM generation (Groq) with template fallback
# ═══════════════════════════════════════════════════════════════════════════════

_LLM_SYSTEM = """You are a career coach and hiring analyst for Shortlist AI.
Generate structured, constructive feedback for a candidate evaluation.
Return ONLY a single valid JSON object — no markdown, no preamble, no trailing text."""

_LLM_USER_TEMPLATE = """CANDIDATE EVALUATION DATA:

Job Title: {job_title}
Composite Score: {composite_score}/100
Tier: {tier}
Recommendation: {recommendation}

Strengths: {strengths}
Skill Gaps: {skill_gaps}
Missing Skills: {missing_skills}
Matched Skills: {matched_skills}
Recommendation Narrative: {narrative}

Produce a JSON object with EXACTLY these keys:

{{
  "why_not_selected": {{
    "reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
    "tone": "constructive",
    "improvement_hints": ["<hint 1>", "<hint 2>"]
  }},
  "improvement_plan": {{
    "short_term": ["<action 1>", "<action 2>", "<action 3>"],
    "long_term": ["<action 1>", "<action 2>"]
  }},
  "learning_path": [
    {{"week": 1, "topic": "<topic>", "resources": ["<resource 1>", "<resource 2>"]}},
    {{"week": 2, "topic": "<topic>", "resources": ["<resource 1>"]}},
    {{"week": 3, "topic": "<topic>", "resources": ["<resource 1>"]}}
  ],
  "candidate_report_markdown": "## Evaluation Summary\\n<full markdown report for the candidate, 200-350 words>",
  "recruiter_summary": "<2-3 sentence plain-English summary for the recruiter>"
}}

Rules:
- reasons in why_not_selected must be specific to the actual skill gaps above
- improvement_plan must address the actual missing skills
- learning_path must cover the top 3 missing skills with real, named resources
- candidate_report_markdown must include: score context, strengths, gaps, next steps
- recruiter_summary must be factual and reference specific skills
- Return ONLY the JSON object, nothing else"""


def _generate_llm_sections(
    evidence: dict,
    role_fit: dict,
    insight: dict,
    ranking: dict,
    skill_viz: dict,
) -> dict:
    """Call Groq to generate narrative sections. Falls back to templates on failure."""
    if settings.use_mock:
        logger.info("feedback_agent: mock mode — using template fallback")
        return _template_fallback(evidence, role_fit, insight, ranking, skill_viz)

    try:
        return _call_groq(evidence, role_fit, insight, ranking, skill_viz)
    except Exception as exc:
        logger.warning("feedback_agent: Groq call failed (%s) — using template fallback", exc)
        return _template_fallback(evidence, role_fit, insight, ranking, skill_viz)


def _call_groq(
    evidence: dict,
    role_fit: dict,
    insight: dict,
    ranking: dict,
    skill_viz: dict,
) -> dict:
    client = _groq_client()

    # Prepare compact inputs for the prompt
    strengths     = insight.get("strengths") or []
    skill_gaps    = [
        g.get("skill_name", str(g)) if isinstance(g, dict) else str(g)
        for g in (insight.get("skill_gaps") or [])
    ]
    
    narrative     = insight.get("recommendation_narrative", "")
    composite     = ranking.get("composite_score", insight.get("score", 0))
    tier          = ranking.get("tier", "")
    recommendation = insight.get("recommendation", "")
    job_title     = role_fit.get("job_title", "Software Engineer")

    user_msg = _LLM_USER_TEMPLATE.format(
        job_title       = job_title,
        composite_score = composite,
        tier            = tier,
        recommendation  = recommendation,
        strengths       = json.dumps(strengths[:6]),
        skill_gaps      = json.dumps(skill_gaps[:6]),
        missing_skills  = json.dumps(skill_viz.get("missing", [])[:8]),
        matched_skills  = json.dumps(skill_viz.get("matched", [])[:8]),
        narrative       = narrative[:400],
    )

    response = client.chat.completions.create(
        model       = settings.GROQ_MODEL,
        messages    = [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature = 0.4,
        max_tokens  = 1800,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    # Validate required keys exist; raise so fallback kicks in if malformed
    for key in ("why_not_selected", "improvement_plan", "learning_path",
                "candidate_report_markdown", "recruiter_summary"):
        if key not in parsed:
            raise ValueError(f"LLM response missing key: {key}")

    return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# Template fallback (no LLM required)
# ═══════════════════════════════════════════════════════════════════════════════

def _template_fallback(
    evidence: dict,
    role_fit: dict,
    insight: dict,
    ranking: dict,
    skill_viz: dict,
) -> dict:
    """
    Deterministic template-based generation.
    Used when GROQ_API_KEY is absent or the LLM call fails.
    """
    missing   = skill_viz.get("missing", [])
    matched   = skill_viz.get("matched", [])
    strengths = insight.get("strengths") or []
    skill_gaps = [
        g.get("skill_name", str(g)) if isinstance(g, dict) else str(g)
        for g in (insight.get("skill_gaps") or [])
    ]
    composite  = float(ranking.get("composite_score") or insight.get("score") or 0)
    tier       = ranking.get("tier", "")
    job_title  = role_fit.get("job_title", "this role")
    narrative  = insight.get("recommendation_narrative", "")

    # ── why_not_selected ──────────────────────────────────────────────────────
    reasons: list[str] = []
    if missing:
        reasons.append(f"Missing required skills: {', '.join(missing[:3])}")
    if skill_gaps:
        reasons.append(f"Skill gaps identified: {', '.join(skill_gaps[:2])}")
    if composite < 60:
        reasons.append("Overall fit score below threshold for this role")
    if not reasons:
        reasons.append("Candidate did not meet all required criteria for this position")

    improvement_hints: list[str] = []
    for skill in missing[:2]:
        improvement_hints.append(f"Build a project demonstrating {skill}")
    if not improvement_hints:
        improvement_hints.append("Strengthen core technical skills relevant to the role")

    # ── improvement_plan ──────────────────────────────────────────────────────
    short_term: list[str] = []
    for skill in missing[:3]:
        short_term.append(f"Learn {skill} fundamentals through hands-on projects")
    if not short_term:
        short_term = ["Review job requirements and identify skill gaps",
                      "Build portfolio projects targeting required skills"]

    long_term: list[str] = [
        "Contribute to open-source projects in the target domain",
        "Pursue relevant certifications or advanced courses",
    ]

    # ── learning_path ─────────────────────────────────────────────────────────
    learning_path: list[dict] = []
    _resource_map = {
        "docker":          ["docs.docker.com", "Docker Getting Started tutorial"],
        "kubernetes":      ["kubernetes.io/docs", "Kubernetes the Hard Way"],
        "aws":             ["AWS Free Tier", "AWS Certified Developer course"],
        "python":          ["docs.python.org", "Real Python tutorials"],
        "react":           ["react.dev", "Full Stack Open (Helsinki)"],
        "typescript":      ["typescriptlang.org/docs", "Total TypeScript"],
        "node.js":         ["nodejs.org/docs", "Node.js official guide"],
        "postgresql":      ["postgresql.org/docs", "pgexercises.com"],
        "system design":   ["Grokking the System Design Interview", "system-design-primer (GitHub)"],
        "fastapi":         ["fastapi.tiangolo.com", "FastAPI tutorial"],
        "machine learning":["fast.ai", "Hands-On ML (Aurélien Géron)"],
    }

    for i, skill in enumerate(missing[:3], start=1):
        skill_lower = skill.lower()
        resources = next(
            (v for k, v in _resource_map.items() if k in skill_lower),
            [f"Official {skill} documentation", f"Search '{skill} tutorial' on YouTube"],
        )
        learning_path.append({
            "week":      i,
            "topic":     f"{skill} fundamentals",
            "resources": resources,
        })

    if not learning_path:
        learning_path = [
            {"week": 1, "topic": "Review job requirements", "resources": ["Job description", "LinkedIn Learning"]},
            {"week": 2, "topic": "Build a portfolio project", "resources": ["GitHub", "freeCodeCamp"]},
        ]

    # ── candidate_report_markdown ─────────────────────────────────────────────
    score_label = "Strong" if composite >= 70 else "Moderate" if composite >= 50 else "Below threshold"
    md_lines = [
        f"## Evaluation Summary — {job_title}",
        "",
        f"**Overall Score:** {composite:.0f}/100 ({score_label})",
        f"**Tier:** {tier.capitalize() if tier else 'N/A'}",
        "",
        "### ✅ Your Strengths",
    ]
    for s in (strengths[:5] or ["Strong technical foundation"]):
        md_lines.append(f"- {s}")

    md_lines += ["", "### 🎯 Areas for Growth"]
    for g in (missing[:4] or skill_gaps[:4] or ["Continue developing core skills"]):
        md_lines.append(f"- {g}")

    md_lines += [
        "",
        "### 🚀 Recommended Next Steps",
        "1. Address the skill gaps listed above with targeted projects",
        "2. Build at least one production-quality project for each missing skill",
        "3. Contribute to open-source to demonstrate real-world collaboration",
        "",
        "### 📝 Evaluator Note",
        narrative or "Keep building — every project strengthens your profile.",
    ]
    candidate_report_markdown = "\n".join(md_lines)

    # ── recruiter_summary ─────────────────────────────────────────────────────
    if matched:
        recruiter_summary = (
            f"This candidate demonstrates strength in {', '.join(matched[:3])} "
            f"but lacks experience in {', '.join(missing[:3]) if missing else 'some required areas'}. "
            f"Overall fit score: {composite:.0f}/100 ({tier})."
        )
    else:
        recruiter_summary = (
            f"Candidate scored {composite:.0f}/100 for {job_title}. "
            f"Key gaps: {', '.join(missing[:3]) if missing else 'see skill analysis'}. "
            "Manual review recommended."
        )

    return {
        "why_not_selected": {
            "reasons":           reasons,
            "tone":              "constructive",
            "improvement_hints": improvement_hints,
        },
        "improvement_plan": {
            "short_term": short_term,
            "long_term":  long_term,
        },
        "learning_path":             learning_path,
        "candidate_report_markdown": candidate_report_markdown,
        "recruiter_summary":         recruiter_summary,
    }
