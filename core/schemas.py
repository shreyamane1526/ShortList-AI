"""
core/schemas.py  — NEW FILE

Single source of truth for every data model in the pipeline.

Ownership rules:
  HiringState.evidence   → Agent 1 writes
  HiringState.role_fit   → Agent 2 writes
  HiringState.insight    → Agent 3 writes
  HiringState.ranking    → Agent 4 writes  [future]
  HiringState.feedback   → Agent 5 writes  [future]

No agent writes another agent's field. Pydantic v2 enforces types at runtime —
if an LLM hallucidates an invalid structure it fails loudly HERE, not silently
in downstream logic.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS — used across all agents
# ═══════════════════════════════════════════════════════════════════════════════

class SkillDepth(str, Enum):
    EXPOSURE   = "exposure"
    WORKING    = "working"
    PRODUCTION = "production"


class Recommendation(str, Enum):
    STRONG_YES = "strong_yes"
    YES        = "yes"
    MAYBE      = "maybe"
    NO         = "no"


class AccessibilityMode(str, Enum):
    STANDARD = "standard"
    ADHD     = "adhd"
    DYSLEXIA = "dyslexia"
    AUTISM   = "autism"


class NDWeight(str, Enum):
    HIGH_SIGNAL   = "high_signal"
    MEDIUM_SIGNAL = "medium_signal"


class FlagSeverity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — Evidence Agent output (SkillProfile / CandidateEvidence)
# ═══════════════════════════════════════════════════════════════════════════════

class SkillItem(BaseModel):
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    depth: SkillDepth
    evidence: List[str]
    recency_days: int
    source: str = "github"          # github | leetcode | portfolio | task_assessment


class IntegrityFlag(BaseModel):
    flag_type: str                  # clone_risk | skill_jump | high_similarity | authorship_mismatch
    severity: FlagSeverity
    detail: str


class IntegritySummary(BaseModel):
    trust_score: int = Field(..., ge=0, le=100)
    flags: List[IntegrityFlag]


class SignalSummary(BaseModel):
    commit_consistency: str         # low | medium | high
    project_complexity: str         # low | medium | high
    domain_breadth: List[str]
    total_repos_analyzed: int
    leetcode_solved: Optional[int] = None
    account_age_days: Optional[int] = None
    dead_repo_count: int = 0


class ScoreBreakdown(BaseModel):
    github_score:       Optional[int]         = None
    github_breakdown:   Optional[Dict]        = None
    leetcode_score:     Optional[int]         = None
    leetcode_breakdown: Optional[Dict]        = None
    portfolio_score:    Optional[int]         = None
    average_score:      Optional[int]         = None


class CandidateEvidence(BaseModel):
    """Output of Agent 1. Credential-free — only verified, observable signals."""
    candidate_id: str
    github_username: str
    name: Optional[str] = None
    collected_at: datetime             = Field(default_factory=datetime.utcnow)
    sources_used: List[str]            = []
    skills: List[SkillItem]            = []
    signals: SignalSummary
    integrity: IntegritySummary
    scores: ScoreBreakdown
    raw_summary: str                   = ""
    hardest_function_summary: str      = ""
    portfolio_text: str                = ""
    # Populated by Inclusion middleware BEFORE Agent 3 sees the data
    nd_flags: List[str]                = []
    task_assessment_score: Optional[float]  = None
    task_assessment_domain: Optional[str]   = None


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — Context Agent output (RoleFitModel)
# ═══════════════════════════════════════════════════════════════════════════════

class SkillMatch(BaseModel):
    """One JD skill matched against candidate's verified skills via cosine similarity."""
    skill_name: str
    required: bool
    match_score: float = Field(..., ge=0.0, le=1.0)
    matched: bool
    importance: float  = Field(default=0.5, ge=0.0, le=1.0)
    candidate_evidence: List[str] = []


class RoleFitModel(BaseModel):
    """Output of Agent 2. Structured JD→candidate alignment from embedding matching."""
    job_title: str
    job_description_raw: str
    job_description_summary: str
    required_skills_matched: List[SkillMatch]
    preferred_skills_matched: List[SkillMatch]
    overall_fit_score: float = Field(..., ge=0.0, le=1.0)
    domains_required: List[str] = []
    jd_embedding_id: Optional[str] = None   # ChromaDB doc ID for retrieval


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — Reasoning Agent output (HiringInsight + BiasAuditReport)
# ═══════════════════════════════════════════════════════════════════════════════

class SkillGap(BaseModel):
    skill_name: str
    severity: str       # critical | moderate | minor
    note: str


class NDStrength(BaseModel):
    signal: str         # debugging_consistency | pattern_recognition | hyperfocus
    evidence: str       # plain-English reason this was flagged
    weight: NDWeight


class ReasoningStep(BaseModel):
    """One step in the decision trace — used for compliance and explainability."""
    step: int
    action: str         # what was evaluated
    data_used: str      # which fields informed this step
    data_ignored: str   # what was masked / excluded
    conclusion: str     # what this step concluded


class BiasAuditReport(BaseModel):
    """
    3.3 — Bias Audit Report.
    Structured, JSON-exportable, reusable across multiple candidates.
    """
    candidate_id: str
    generated_at: datetime              = Field(default_factory=datetime.utcnow)
    nd_signal_detected: bool
    proxies_removed: List[str]          # which bias proxies were structurally masked
    fairness_score: float               = Field(..., ge=0.0, le=1.0)
    selection_factors: List[str]        # what positively influenced the decision
    risk_flags: List[str]               # remaining bias risk indicators
    nd_strength_uplifts: List[str]      # signals that boosted the recommendation
    recommendation_before_inclusion: str  # what the raw score would have been
    recommendation_after_inclusion: str   # final recommendation after ND weighting


class HiringInsight(BaseModel):
    """Output of Agent 3 — explainable hiring decision for one candidate."""
    candidate_id: str
    # Core decision
    score: int = Field(..., ge=0, le=100)       # 0–100 hiring score
    recommendation: Recommendation
    recommendation_narrative: str               # 2–3 sentence plain English
    # Evidence breakdown
    strengths: List[str]
    skill_gaps: List[SkillGap]
    confidence_per_skill: Dict[str, float]
    nd_strengths: List[NDStrength]
    # Compliance artifacts
    reasoning_steps: List[ReasoningStep]        # step-by-step decision trace
    reasoning_trace: str                        # compact single-string version
    bias_audit: BiasAuditReport
    # Accessibility
    accessible_summary: Optional[str] = None   # reformatted for ND candidates


# ═══════════════════════════════════════════════════════════════════════════════
# RANKING (Agent 4 — future)
# ═══════════════════════════════════════════════════════════════════════════════

class CandidateRank(BaseModel):
    """One entry in a ranked shortlist. Produced by Agent 4."""
    rank: int
    candidate_id: str
    score: int
    recommendation: str
    justification: str
    similarity_score: Optional[float] = None   # cosine sim vs JD embedding


class ShortlistResult(BaseModel):
    """Full ranked shortlist for one job. Produced by Agent 4."""
    job_title: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_candidates: int
    shortlisted: List[CandidateRank]
    cutoff_score: int


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE STATE — the object that flows through all LangGraph nodes
# ═══════════════════════════════════════════════════════════════════════════════

class AccessibilityProfile(BaseModel):
    mode: AccessibilityMode              = AccessibilityMode.STANDARD
    tts_enabled: bool                    = False
    step_by_step: bool                   = False
    simplified_language: bool            = False


class CandidateNDSelfID(BaseModel):
    neurodivergent: Optional[bool] = None
    nd_type: Optional[str] = None


class HiringState(BaseModel):
    """
    Single object flowing through the entire LangGraph pipeline.
    Each agent reads what it needs and ONLY writes its own assigned field.
    """
    # ── Pipeline inputs (set at entry) ──────────────────────────────────────
    candidate_id: str
    github_username: str
    job_description: str
    accessibility_profile: AccessibilityProfile = Field(
        default_factory=AccessibilityProfile
    )
    leetcode_username: Optional[str]     = None
    portfolio_url: Optional[str]         = None
    resume_url: Optional[str]            = None
    candidate_nd_self_id: Optional[CandidateNDSelfID] = None
    inclusion_enabled: bool              = True

    # ── Agent outputs (each agent writes exactly one field) ─────────────────
    evidence: Optional[CandidateEvidence] = None   # Agent 1
    role_fit: Optional[RoleFitModel]      = None   # Agent 2
    insight:  Optional[HiringInsight]     = None   # Agent 3
    ranking:  Optional[ShortlistResult]   = None   # Agent 4 [future]
    feedback_report: Optional[Dict]       = None   # Agent 5 [future]

    # ── Bookkeeping ──────────────────────────────────────────────────────────
    errors: List[str]                     = []
    pipeline_started_at: datetime         = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# API REQUEST / RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

class PipelineRequest(BaseModel):
    candidate_id: str
    github_username: str
    job_description: str
    leetcode_username: Optional[str]     = None
    portfolio_url: Optional[str]         = None
    resume_url: Optional[str]            = None
    accessibility_mode: AccessibilityMode = AccessibilityMode.STANDARD
    candidate_nd_self_id: Optional[CandidateNDSelfID] = None
    inclusion_enabled: bool              = True


class RecruiterFeedbackRequest(BaseModel):
    model_config = {
        "protected_namespaces": (),
    }

    candidate_id: str
    ai_prediction: Dict[str, Any] | str
    recruiter_decision: str
    override_reason: Optional[str] = None
    final_hiring_outcome: Optional[str] = None
    jd_hash: Optional[str] = None
    model_version: Optional[str] = None


class RecruiterFeedbackResponse(BaseModel):
    id: int
    candidate_id: str
    recruiter_decision: str
    final_hiring_outcome: Optional[str] = None
    created_at: datetime


class PipelineResponse(BaseModel):
    candidate_id: str
    score: Optional[int]                 = None
    recommendation: Optional[str]        = None
    recommendation_narrative: Optional[str] = None
    strengths: List[str]                 = []
    skill_gaps: List[Dict]               = []
    nd_strengths: List[Dict]             = []
    confidence_per_skill: Dict[str, float] = {}
    overall_fit_score: Optional[float]   = None
    trust_score: Optional[int]           = None
    bias_audit: Optional[Dict]           = None
    reasoning_steps: List[Dict]          = []
    accessible_summary: Optional[str]    = None
    nd_inclusion: Optional[Dict[str, Any]] = None   # NDInclusionReport
        # ── Agent 5 — Feedback Agent ────────────────────────────────

    why_not_selected: Optional[Dict[str, Any]] = None

    improvement_plan: Optional[Dict[str, Any]] = None

    learning_path: List[Dict[str, Any]] = []

    learning_roadmap: Optional[Dict[str, Any]] = None

    skill_match_visualization: Optional[
        Dict[str, Any]
    ] = None

    confidence_score: Optional[
        Dict[str, Any]
    ] = None

    badges: List[str] = []

    candidate_report_markdown: Optional[
        str
    ] = None

    recruiter_summary: Optional[
        str
    ] = None
    errors: List[str]                    = []
    pipeline_duration_seconds: Optional[float] = None
