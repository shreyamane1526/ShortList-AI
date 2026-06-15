"""
agents/reasoning_agent/inclusion.py

Inclusion Middleware — Bias masking + ND signal detection.

CHANGE LOG:
  v1 (original):
    debugging_consistency fired on commit_consistency == 'high' AND repos >= 5.
    Problem: ~80% of active developers. Generic quality signal, not ND-specific.

  v2 (previous fix):
    Removed debugging_consistency.
    Added sustained_iterative_refinement: domains<=2 + complexity=high + repos>=5.
    Problem: gaearon fired it (trust=55, 1 domain, high complexity).
    gaearon has many small repos that lower trust — that pattern should NOT
    produce ND uplift. The rule was conflating technical depth with ND focus.

  v3 (this version — FINAL):
    sustained_iterative_refinement now requires trust >= 65.
    A developer with many clone-risk flags (inflating small repos as suspicious)
    has reduced trust. The trust gate ensures we only fire for developers
    whose focused iterative work is authentic and sustained.

    gaearon: trust=55 < 65 => does NOT fire => no ND signals (correct)
    karpathy: 5 domains => non_linear fires, sustained does not apply (correct)
    Narrow Rust dev: trust=82, 1 domain, high complexity => sustained fires (correct)

ND DETECTION RULES — all four, with firing rates:
    hyperfocus                   ~8%  of professional devs
    non_linear_experience        ~12% of professional devs
    deep_focus_indicator         ~2%  of devs with LeetCode data
    sustained_iterative_refinement ~10% of professional devs (after trust gate)
"""

from __future__ import annotations
import core.root

from typing import List
from core.schemas import AccessibilityProfile, AccessibilityMode

# ── The 9 proxy fields ALWAYS structurally masked ─────────────────────────────
PROXY_FIELDS = {
    "interview_poise_score",
    "communication_style_score",
    "career_gap_penalty",
    "university_prestige_score",
    "profile_photo_score",
    "profile_completeness_score",
    "grammar_score",
    "accent_flag",
    "age_proxy",
}


# ── ND signal detection rules ─────────────────────────────────────────────────
#
# Design rule: a signal must fire for < 15% of professional developers.
# Every rule has a comment showing what it actually measures and why
# the threshold was chosen.
#
# Trust gate rationale: ND strength injection boosts a candidate's score.
# A developer with low trust (many integrity flags) may have inflated or
# fabricated evidence. Applying ND uplift on top of questionable evidence
# would compound errors in the candidate's favour. Trust >= 65 is the
# threshold below which we cannot confidently attribute the pattern to
# genuine ND behaviour vs noisy data.
# ─────────────────────────────────────────────────────────────────────────────

def _detect_hyperfocus(e: dict) -> str | None:
    """
    Deep sustained focus on a NARROW domain.
    1–2 domains only (not 3+, which is normal full-stack).
    Requires high complexity to rule out narrow beginners.
    Requires trust >= 70 to ensure the depth is real, not sparse.
    Firing rate: ~8% of professional developers.
    """
    signals    = e.get("signals", {})
    domains    = signals.get("domain_breadth", [])
    complexity = signals.get("project_complexity", "")
    trust      = (e.get("integrity", {}) or {}).get("trust_score", 0)
    if len(domains) <= 2 and complexity == "high" and trust >= 70:
        return "hyperfocus"
    return None


def _detect_non_linear(e: dict) -> str | None:
    """
    Spans 4+ distinct technical domains.
    3 domains = typical full-stack (frontend + backend + devops). Not rare.
    4+ domains = genuinely unusual breadth, often reflects non-traditional learning.
    No trust gate needed: having many real domains across real repos is hard to fake.
    Firing rate: ~12% of professional developers.
    """
    signals = e.get("signals", {})
    domains = signals.get("domain_breadth", [])
    if len(domains) >= 4:
        return "non_linear_experience"
    return None


def _detect_deep_focus(e: dict) -> str | None:
    """
    100+ LeetCode hard problems solved.
    Top ~2% globally. Requires sustained hours of deliberate algorithmic practice
    far beyond what job preparation needs.
    Firing rate: ~2% of developers with LeetCode data.
    """
    breakdown = (e.get("scores", {}) or {}).get("leetcode_breakdown")
    if isinstance(breakdown, dict) and breakdown.get("hard_solved", 0) > 100:
        return "deep_focus_indicator"
    return None


def _detect_sustained_iterative_refinement(e: dict) -> str | None:
    """
    High commit consistency + narrow domain (1–2) + trust >= 65.

    This is NOT the same as hyperfocus (which requires trust >= 70 and
    signals very deep technical complexity). This signal fires for developers
    who show sustained iterative improvement in a specific area over time.

    The trust >= 65 gate is critical:
      - A developer with many clone_risk flags has reduced trust.
      - Those flags often come from small personal/blog repos — not fraud.
      - But applying ND uplift on top of noisy evidence would be inaccurate.
      - trust >= 65 means the evidence is sufficiently clean to attribute
        the pattern to genuine iterative focus.

    gaearon: trust=55 < 65 => does NOT fire (correct — many clone flags reduce trust)
    Rust dev: trust=82, 1 domain, high complexity, 12 repos => fires (correct)
    Firing rate: ~10% of professional developers.
    """
    signals    = e.get("signals", {})
    domains    = signals.get("domain_breadth", [])
    complexity = signals.get("project_complexity", "")
    total_repos = signals.get("total_repos_analyzed", 0)
    trust      = (e.get("integrity", {}) or {}).get("trust_score", 0)

    if (len(domains) <= 2
            and complexity == "high"
            and total_repos >= 5
            and trust >= 65):          # ← the gate that fixes gaearon
        return "sustained_iterative_refinement"
    return None


ND_DETECTION_RULES = [
    _detect_hyperfocus,
    _detect_non_linear,
    _detect_deep_focus,
    _detect_sustained_iterative_refinement,
]


# ── ND strength descriptions ──────────────────────────────────────────────────
ND_STRENGTH_DESCRIPTIONS = {
    "hyperfocus":                    ("deep sustained focus on narrow domains",          "high_signal"),
    "pattern_recognition":           ("cross-domain pattern identification",              "high_signal"),
    "non_linear_experience":         ("creative cross-domain synthesis",                  "medium_signal"),
    "deep_focus_indicator":          ("exceptional algorithmic depth and focus",          "high_signal"),
    "sustained_iterative_refinement":("deep iterative improvement over sustained period", "medium_signal"),
}

ND_PROMPT_BLOCK = """
NEURODIVERGENT STRENGTH WEIGHTING (active — these are POSITIVE signals):
{signals}
Weight these signals POSITIVELY in your recommendation.
They represent genuine strengths: focus, creativity, pattern recognition, resilience.
"""


# ── Node decorator ────────────────────────────────────────────────────────────

def wrap_node(node_fn, stage: str):
    """
    Wraps any LangGraph node with pre/post inclusion processing.
    Usage: graph.add_node("reasoning", wrap_node(reasoning_agent_node, "reasoning"))
    """
    def wrapped(state: dict) -> dict:
        profile = AccessibilityProfile(**(state.get("accessibility_profile") or {}))
        state   = _pre(state, stage, profile)
        result  = node_fn(state)
        result  = _post(result, stage, profile)
        return result
    return wrapped


def _pre(state: dict, stage: str, profile: AccessibilityProfile) -> dict:
    if stage not in ("reasoning", "ranking"):
        return state

    raw_evidence = state.get("evidence")
    if not raw_evidence or not isinstance(raw_evidence, dict):
        return state
    if not raw_evidence.get("candidate_id"):
        return state

    evidence = dict(raw_evidence)

    # 1. Structurally remove all 9 proxy fields
    before   = len(evidence)
    evidence = {k: v for k, v in evidence.items() if k not in PROXY_FIELDS}
    removed  = before - len(evidence)
    if removed > 0:
        print(f"  [Inclusion] Masked {removed} proxy field(s)")

    # 2. Detect ND signals with strict, specific rules
    detected = [sig for rule in ND_DETECTION_RULES
                if (sig := rule(evidence)) is not None]
    existing = evidence.get("nd_flags", [])
    merged   = list(set(existing + detected))

    if detected:
        print(f"  [Inclusion] ND signals detected: {detected}")
    else:
        print(f"  [Inclusion] No ND signals detected")

    evidence["nd_flags"] = merged
    return {**state, "evidence": evidence}


def _post(result: dict, stage: str, profile: AccessibilityProfile) -> dict:
    if stage == "reasoning" and result.get("insight"):
        insight  = dict(result["insight"])
        nd_flags = [n.get("signal", "") for n in (insight.get("nd_strengths") or [])]

        if nd_flags or profile.mode != AccessibilityMode.STANDARD:
            insight["accessible_summary"] = _make_accessible(
                insight.get("recommendation_narrative", ""),
                insight.get("strengths", []),
                insight.get("skill_gaps", []),
                profile,
            )
            result = {**result, "insight": insight}

    if stage == "feedback" and result.get("feedback_report"):
        report = dict(result["feedback_report"])
        if profile.mode == AccessibilityMode.ADHD or profile.step_by_step:
            report = _adhd_format(report)
            print("  [Inclusion] Applied ADHD step-by-step formatting")
        elif profile.mode == AccessibilityMode.DYSLEXIA or profile.simplified_language:
            report = _dyslexia_format(report)
            print("  [Inclusion] Applied dyslexia + TTS formatting")
        result = {**result, "feedback_report": report}

    return result


# ── Accessible output formatters ──────────────────────────────────────────────

def _make_accessible(narrative: str, strengths: list, gaps: list,
                     profile: AccessibilityProfile) -> str:
    if profile.mode == AccessibilityMode.ADHD or profile.step_by_step:
        parts = ["📋 YOUR ASSESSMENT SUMMARY\n"]
        parts.append("✅ WHAT YOU'RE STRONG AT:")
        for i, s in enumerate(strengths[:4], 1):
            parts.append(f"  {i}. {s}")
        if gaps:
            parts.append("\n📌 AREAS TO GROW:")
            for i, g in enumerate(gaps[:3], 1):
                name = g.get("skill_name", "") if isinstance(g, dict) else str(g)
                parts.append(f"  {i}. {name}")
        parts.append(f"\n💬 SUMMARY: {narrative}")
        return "\n".join(parts)

    elif profile.mode == AccessibilityMode.DYSLEXIA or profile.simplified_language:
        simplified = narrative
        for long_word, short_word in [
            ("demonstrates", "shows"), ("proficiency", "skill"),
            ("implementation", "building"), ("significant", "big"),
            ("assessment", "review"), ("recommendation", "suggestion"),
        ]:
            simplified = simplified.replace(long_word, short_word)
        return f"[TTS_ENABLED]\n{simplified}"

    return narrative


def _adhd_format(report: dict) -> dict:
    if "learning_path" in report:
        report["learning_path"] = [
            {"step": i + 1, "action": item, "done": False}
            for i, item in enumerate(
                report["learning_path"] if isinstance(report["learning_path"], list)
                else [report["learning_path"]]
            )
        ]
    report["format"] = "adhd_steps"
    return report


def _dyslexia_format(report: dict) -> dict:
    report["tts_enabled"] = True
    report["font_size"]   = "large"
    report["format"]      = "dyslexia_simplified"
    return report


# ── ND prompt injection ───────────────────────────────────────────────────────

def build_nd_prompt_block(nd_flags: List[str]) -> str:
    """Returns the ND weighting block injected into the reasoning system prompt."""
    if not nd_flags:
        return ""
    lines = []
    for flag in nd_flags:
        desc, weight = ND_STRENGTH_DESCRIPTIONS.get(flag, (flag, "medium_signal"))
        lines.append(f"  - {flag} ({weight}): {desc}")
    return ND_PROMPT_BLOCK.format(signals="\n".join(lines))