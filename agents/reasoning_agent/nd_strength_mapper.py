"""
agents/reasoning_agent/nd_strength_mapper.py  — NEW FILE

PURPOSE:
  Maps raw evidence signals (GitHub, LeetCode, portfolio, task assessment)
  to typed ND strength objects.

DESIGN PRINCIPLES:
  1. Deterministic — same evidence always produces same mapping
  2. No labels exposed to LLM — internal only
  3. No reverse bias — strengths are ADDITIONS, never override core score
  4. Trait→Strength mapping is grounded in published research on ND cognition
  5. Signals fire only on SPECIFIC patterns, not generic quality markers

TRAIT → STRENGTH MAPPING (research-grounded):

  ADHD:
    hyperfocus        → sustained deep work on one area over long periods
    rapid_ideation    → many diverse small repos / branches / experiments
    debug_persistence → high ratio of fix/patch commits across history

  DYSLEXIA:
    visual_thinking   → diagram-heavy commits, CSS/SVG/canvas heavy work
    systems_thinking  → architectural-level code (config, infra, abstractions)
    big_picture_reasoning → cross-cutting contributions, refactors at scale

  AUTISM:
    pattern_recognition → consistent naming, systematic testing, low variance style
    deep_focus          → narrow domain, very high depth score, long commit streaks
    consistency         → commit regularity metrics, low style variance

UNDERESTIMATION RISK:
  Some ND patterns cause standard metrics to UNDERCOUNT real ability:
  - Non-linear career → fewer matched keywords → lower required_match_ratio
  - Hyperfocus narrow domain → fewer matched preferred skills
  - Communication differences → lower portfolio_text richness
  These are detected and flagged here as risk factors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ══════════════════════════════════════════════════════════════════════════════
# Output types
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NDStrengthSignal:
    """One detected ND strength with its evidence and the trait cluster it maps to."""
    signal_name:  str          # e.g. "hyperfocus", "debug_persistence"
    trait_cluster: str         # "adhd" | "dyslexia" | "autism" | "general"
    evidence:     str          # plain English — what was observed
    strength_label: str        # the hiring-neutral strength label
    weight:       str          # "high_signal" | "medium_signal"


@dataclass
class NDUnderestimationRisk:
    """Flags where standard metrics systematically undercount an ND candidate's real ability."""
    risk_factor:  str          # e.g. "narrow_domain_hyperfocus"
    description:  str          # plain English
    affected_metric: str       # which pipeline metric this distorts
    severity:     str          # "high" | "medium" | "low"


@dataclass
class NDMappingResult:
    """Complete ND mapping output for one candidate."""
    candidate_id:          str
    signals:               List[NDStrengthSignal]
    underestimation_risks: List[NDUnderestimationRisk]
    dominant_trait_cluster: Optional[str]      # "adhd"|"dyslexia"|"autism"|None
    nd_score:              float               # 0.0–1.0 aggregate strength score
    penalty_reduction_weight: float            # how much to reduce gap penalties (0.0–0.2)
    summary:               str                # one-line neutral summary for LLM


# ══════════════════════════════════════════════════════════════════════════════
# Detection rules — one function per signal
# ══════════════════════════════════════════════════════════════════════════════

def _detect_hyperfocus(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    ADHD: hyperfocus
    Evidence: 1-2 domains only + high complexity + high GitHub activity + sustained over time
    NOT fired by: just having high complexity (that's normal for good engineers)
    """
    signals   = e.get("signals", {})
    domains   = signals.get("domain_breadth", [])
    complexity = signals.get("project_complexity", "")
    trust     = (e.get("integrity", {}) or {}).get("trust_score", 0)
    total_repos = signals.get("total_repos_analyzed", 0)

    if len(domains) <= 2 and complexity == "high" and trust >= 65 and total_repos >= 4:
        return NDStrengthSignal(
            signal_name   = "hyperfocus",
            trait_cluster = "adhd",
            evidence      = (f"Deep specialisation in {len(domains)} domain(s) with high project "
                             f"complexity across {total_repos} repos — sustained focused contribution pattern"),
            strength_label= "Sustained deep-work capability in specialist domains",
            weight        = "high_signal",
        )
    return None


def _detect_rapid_ideation(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    ADHD: rapid_ideation
    Evidence: many repos (5+) across 3+ domains — breadth of experimentation
    AND low dead_repo_count (shows follow-through, not just starting things)
    """
    signals    = e.get("signals", {})
    domains    = signals.get("domain_breadth", [])
    total_repos = signals.get("total_repos_analyzed", 0)
    dead_repos  = signals.get("dead_repo_count", 0)
    active_repos = max(0, total_repos - dead_repos)

    if len(domains) >= 3 and active_repos >= 6 and dead_repos <= total_repos * 0.3:
        return NDStrengthSignal(
            signal_name   = "rapid_ideation",
            trait_cluster = "adhd",
            evidence      = (f"{active_repos} active repos across {len(domains)} domains — "
                             f"broad experimentation with strong follow-through"),
            strength_label= "Cross-domain problem framing and rapid prototyping",
            weight        = "medium_signal",
        )
    return None


def _detect_debug_persistence(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    ADHD: debug_persistence
    Evidence: high commit consistency + LeetCode hard problem count > 20
    The LeetCode hard signal indicates persistence on difficult problems, not speed.
    """
    signals     = e.get("signals", {})
    consistency = signals.get("commit_consistency", "")
    total_repos  = signals.get("total_repos_analyzed", 0)

    lc_hard = 0
    if lc and not lc.get("not_found") and not lc.get("error"):
        lc_hard = lc.get("hard_solved", 0) or 0

    if consistency == "high" and total_repos >= 5 and lc_hard >= 20:
        return NDStrengthSignal(
            signal_name   = "debug_persistence",
            trait_cluster = "adhd",
            evidence      = (f"High commit consistency across {total_repos} repos + "
                             f"{lc_hard} hard LeetCode problems solved — persistent problem engagement"),
            strength_label= "Persistent debugging and iterative problem-solving stamina",
            weight        = "high_signal",
        )
    return None


def _detect_visual_thinking(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    DYSLEXIA: visual_thinking
    Evidence: frontend/mobile domain presence + CSS/SVG/canvas skill signals
    OR: portfolio has diagram/architecture keywords
    """
    signals  = e.get("signals", {})
    domains  = signals.get("domain_breadth", [])
    portfolio = (e.get("portfolio_text") or "").lower()
    skills   = [s.get("name","").lower() for s in e.get("skills", [])]

    visual_skills = {"css","svg","canvas","figma","d3","three.js","animation","ui","ux"}
    visual_keywords = {"diagram","architecture","visual","flow","layout","wireframe","sketch"}

    has_visual_skill = any(s in visual_skills for s in skills)
    has_visual_portfolio = any(kw in portfolio for kw in visual_keywords)
    has_visual_domain = "frontend" in domains or "mobile" in domains

    if (has_visual_skill or has_visual_portfolio) and has_visual_domain:
        return NDStrengthSignal(
            signal_name   = "visual_thinking",
            trait_cluster = "dyslexia",
            evidence      = "Visual/spatial skill signals in portfolio or code — strong spatial problem representation",
            strength_label= "Visual and spatial reasoning applied to technical problem-solving",
            weight        = "medium_signal",
        )
    return None


def _detect_systems_thinking(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    DYSLEXIA: systems_thinking
    Evidence: devops/infrastructure domain + high complexity
    Infrastructure work requires holding entire system in mind simultaneously.
    """
    signals    = e.get("signals", {})
    domains    = signals.get("domain_breadth", [])
    complexity = signals.get("project_complexity", "")
    skills     = [s.get("name","").lower() for s in e.get("skills", [])]

    infra_skills  = {"docker","kubernetes","terraform","aws","gcp","ansible","nginx","systemd"}
    has_infra     = any(s in infra_skills for s in skills)
    has_devops    = "devops" in domains or "systems" in domains

    if (has_infra or has_devops) and complexity in ("high", "medium"):
        return NDStrengthSignal(
            signal_name   = "systems_thinking",
            trait_cluster = "dyslexia",
            evidence      = f"Infrastructure/systems domain work with {complexity} complexity — holistic system design pattern",
            strength_label= "Holistic systems design and cross-component reasoning",
            weight        = "high_signal",
        )
    return None


def _detect_big_picture_reasoning(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    DYSLEXIA: big_picture_reasoning
    Evidence: multiple refactoring commits in summary OR architectural skills
    (refactoring requires understanding the whole before restructuring the parts)
    """
    summary   = (e.get("raw_summary") or "").lower()
    portfolio = (e.get("portfolio_text") or "").lower()
    skills    = [s.get("name","").lower() for s in e.get("skills", [])]

    arch_keywords = {"refactor","architect","design pattern","abstraction","microservice",
                     "system design","api design","scalab"}
    arch_skills   = {"graphql","grpc","kafka","redis","elasticsearch","system design"}

    has_arch_keyword = any(kw in summary or kw in portfolio for kw in arch_keywords)
    has_arch_skill   = any(s in arch_skills for s in skills)

    if has_arch_keyword or has_arch_skill:
        return NDStrengthSignal(
            signal_name   = "big_picture_reasoning",
            trait_cluster = "dyslexia",
            evidence      = "Architectural and refactoring patterns detected — macro-level design thinking",
            strength_label= "Architectural thinking and macro-level technical design",
            weight        = "medium_signal",
        )
    return None


def _detect_pattern_recognition(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    AUTISM: pattern_recognition
    Evidence: high LeetCode medium+hard count — pattern-based algorithmic thinking
    AND consistent commit naming (inferred from high trust + high consistency)
    """
    lc_medium = lc_hard = 0
    if lc and not lc.get("not_found") and not lc.get("error"):
        lc_medium = lc.get("medium_solved", 0) or 0
        lc_hard   = lc.get("hard_solved", 0) or 0

    signals     = e.get("signals", {})
    consistency = signals.get("commit_consistency", "")
    trust       = (e.get("integrity", {}) or {}).get("trust_score", 0)

    if (lc_medium + lc_hard) >= 80 and consistency == "high" and trust >= 60:
        return NDStrengthSignal(
            signal_name   = "pattern_recognition",
            trait_cluster = "autism",
            evidence      = (f"{lc_medium} medium + {lc_hard} hard LeetCode problems with consistent "
                             f"commit discipline — systematic pattern identification"),
            strength_label= "Systematic pattern identification and algorithmic reasoning",
            weight        = "high_signal",
        )
    return None


def _detect_deep_focus(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    AUTISM: deep_focus
    Evidence: extremely high LeetCode hard count (100+) OR task assessment score >= 0.90
    Exceptional depth in a narrow problem class — the defining autism strength in technical work.
    """
    lc_hard = 0
    if lc and not lc.get("not_found") and not lc.get("error"):
        lc_hard = lc.get("hard_solved", 0) or 0

    ta_score = ta.get("score", 0) or 0

    if lc_hard >= 100:
        return NDStrengthSignal(
            signal_name   = "deep_focus",
            trait_cluster = "autism",
            evidence      = f"{lc_hard} hard LeetCode problems solved — exceptional depth of algorithmic focus",
            strength_label= "Exceptional algorithmic depth and sustained cognitive focus",
            weight        = "high_signal",
        )
    if ta_score >= 0.90:
        return NDStrengthSignal(
            signal_name   = "deep_focus",
            trait_cluster = "autism",
            evidence      = f"Task assessment score {ta_score:.0%} — exceptional performance under structured conditions",
            strength_label= "High performance under clear, structured task conditions",
            weight        = "high_signal",
        )
    return None


def _detect_consistency(e: dict, lc: dict, ta: dict) -> Optional[NDStrengthSignal]:
    """
    AUTISM: consistency
    Evidence: high commit consistency + low dead repo count + high trust
    Autistic developers often produce remarkably consistent, well-structured work.
    """
    signals     = e.get("signals", {})
    consistency = signals.get("commit_consistency", "")
    total_repos  = signals.get("total_repos_analyzed", 0)
    dead_repos   = signals.get("dead_repo_count", 0)
    trust       = (e.get("integrity", {}) or {}).get("trust_score", 0)

    dead_ratio = dead_repos / max(total_repos, 1)

    if consistency == "high" and trust >= 75 and dead_ratio <= 0.15 and total_repos >= 4:
        return NDStrengthSignal(
            signal_name   = "consistency",
            trait_cluster = "autism",
            evidence      = (f"High commit consistency, {dead_ratio:.0%} dead repo ratio, "
                             f"trust score {trust}/100 — systematic, reliable output pattern"),
            strength_label= "Systematic and consistent code delivery with high reliability",
            weight        = "medium_signal",
        )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Underestimation risk detectors
# ══════════════════════════════════════════════════════════════════════════════

def _detect_underestimation_risks(
    e: dict, role_fit: dict, signals: List[NDStrengthSignal]
) -> List[NDUnderestimationRisk]:
    """
    Detects where standard pipeline metrics systematically undercount
    a candidate whose ND profile produces non-standard evidence patterns.
    """
    risks = []
    ev_signals  = e.get("signals", {})
    domains     = ev_signals.get("domain_breadth", [])
    total_repos  = ev_signals.get("total_repos_analyzed", 0)
    portfolio   = (e.get("portfolio_text") or "").strip()

    req_matched = sum(
        1 for s in role_fit.get("required_skills_matched", [])
        if s.get("matched")
    )
    req_total = len(role_fit.get("required_skills_matched", []))
    req_ratio = req_matched / max(req_total, 1)

    nd_clusters = {s.trait_cluster for s in signals}

    # Risk 1: Narrow hyperfocus domain causes low required_match_ratio
    if "adhd" in nd_clusters or "autism" in nd_clusters:
        if len(domains) <= 2 and req_ratio < 0.45:
            risks.append(NDUnderestimationRisk(
                risk_factor    = "narrow_domain_hyperfocus",
                description    = (f"Candidate has deep specialisation in {len(domains)} domain(s). "
                                  f"Narrow domain focus (a common ND strength pattern) causes low "
                                  f"keyword coverage across the JD, underestimating transferable ability."),
                affected_metric = "required_match_ratio",
                severity       = "high",
            ))

    # Risk 2: Non-linear career path causes skill keyword gaps
    if len(domains) >= 4 and req_ratio < 0.50:
        risks.append(NDUnderestimationRisk(
            risk_factor    = "non_linear_career_path",
            description    = (f"Candidate spans {len(domains)} domains — a non-linear career trajectory "
                              f"common in ND developers. Standard JD keyword matching misses "
                              f"cross-domain transferable skills."),
            affected_metric = "required_match_ratio",
            severity       = "medium",
        ))

    # Risk 3: Low portfolio richness (dyslexia pattern — written output reduced)
    if "dyslexia" in nd_clusters and not portfolio:
        risks.append(NDUnderestimationRisk(
            risk_factor    = "reduced_written_portfolio",
            description    = ("Portfolio text is minimal or absent. Dyslexic developers "
                              "often demonstrate ability through code rather than written descriptions, "
                              "causing portfolio-based signals to undercount real capability."),
            affected_metric = "has_portfolio / portfolio_score",
            severity       = "medium",
        ))

    # Risk 4: Communication-style gap penalty (autism pattern)
    if "autism" in nd_clusters:
        risks.append(NDUnderestimationRisk(
            risk_factor    = "communication_style_difference",
            description    = ("Commit messages and documentation may be terse or technically precise "
                              "rather than elaborative. Standard documentation-richness signals "
                              "may penalise this style despite high technical quality."),
            affected_metric = "raw_summary / portfolio richness",
            severity       = "low",
        ))

    return risks


# ══════════════════════════════════════════════════════════════════════════════
# Penalty reduction computation
# ══════════════════════════════════════════════════════════════════════════════

def _compute_penalty_reduction(
    signals: List[NDStrengthSignal],
    risks: List[NDUnderestimationRisk],
) -> float:
    """
    Computes a penalty reduction weight (0.0–0.2).

    This is applied in feature_engineer.py to reduce the gap penalty
    contribution when underestimation risk is present.

    CEILING of 0.20 is HARD — this cannot override more than 20% of the
    gap penalty. This prevents reverse bias.

    Formula:
      base = 0.05 per high_signal ND strength
      base = 0.02 per medium_signal ND strength
      risk_bonus = 0.03 per high severity underestimation risk
      risk_bonus = 0.01 per medium severity risk
      total = min(0.20, base + risk_bonus)
    """
    base = sum(
        0.05 if s.weight == "high_signal" else 0.02
        for s in signals
    )
    risk_bonus = sum(
        0.03 if r.severity == "high" else (0.01 if r.severity == "medium" else 0.0)
        for r in risks
    )
    return round(min(0.20, base + risk_bonus), 4)


# ══════════════════════════════════════════════════════════════════════════════
# ND score
# ══════════════════════════════════════════════════════════════════════════════

def _compute_nd_score(signals: List[NDStrengthSignal]) -> float:
    """
    Aggregate ND strength score: 0.0–1.0.
    High signals contribute 0.25, medium signals 0.12.
    Capped at 1.0.
    """
    raw = sum(0.25 if s.weight == "high_signal" else 0.12 for s in signals)
    return round(min(1.0, raw), 4)


# ══════════════════════════════════════════════════════════════════════════════
# Dominant trait cluster
# ══════════════════════════════════════════════════════════════════════════════

def _dominant_cluster(signals: List[NDStrengthSignal]) -> Optional[str]:
    if not signals:
        return None
    counts: dict = {}
    for s in signals:
        counts[s.trait_cluster] = counts.get(s.trait_cluster, 0) + (
            2 if s.weight == "high_signal" else 1
        )
    return max(counts, key=lambda k: counts[k])


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

ALL_DETECTORS = [
    _detect_hyperfocus,
    _detect_rapid_ideation,
    _detect_debug_persistence,
    _detect_visual_thinking,
    _detect_systems_thinking,
    _detect_big_picture_reasoning,
    _detect_pattern_recognition,
    _detect_deep_focus,
    _detect_consistency,
]


def map_nd_strengths(
    evidence: dict,
    role_fit: dict,
    leetcode_data: dict = None,
    task_assessment: dict = None,
) -> NDMappingResult:
    """
    Main entry point. Takes raw evidence + role_fit dicts.
    Returns a complete NDMappingResult.

    Args:
        evidence:        CandidateEvidence as dict (from HiringState)
        role_fit:        RoleFitModel as dict (from HiringState)
        leetcode_data:   Raw LeetCode collector output (optional, improves detection)
        task_assessment: Task assessment result dict: {"score": 0.0-1.0, "domain": "..."}
    """
    lc = leetcode_data or {}
    ta = task_assessment or {}

    # Run all detectors
    raw_signals = [d(evidence, lc, ta) for d in ALL_DETECTORS]
    signals = [s for s in raw_signals if s is not None]

    # Detect underestimation risks
    risks = _detect_underestimation_risks(evidence, role_fit, signals)

    # Aggregate
    dominant  = _dominant_cluster(signals)
    nd_score  = _compute_nd_score(signals)
    penalty_r = _compute_penalty_reduction(signals, risks)

    # Neutral summary (no labels — safe for LLM ingestion)
    if signals:
        strength_labels = [s.strength_label for s in signals[:3]]
        summary = "Detected strengths: " + "; ".join(strength_labels)
    else:
        summary = "No specific ND strength patterns detected from available evidence."

    return NDMappingResult(
        candidate_id           = evidence.get("candidate_id", "unknown"),
        signals                = signals,
        underestimation_risks  = risks,
        dominant_trait_cluster = dominant,
        nd_score               = nd_score,
        penalty_reduction_weight = penalty_r,
        summary                = summary,
    )