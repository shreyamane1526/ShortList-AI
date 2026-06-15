# LinedInHackathon/schemas.py
"""
schemas.py — DEPRECATED

This file is kept only for backward compatibility.
All data models have been consolidated into core/schemas.py.

Import from there instead:
    from core.schemas import HiringState, PipelineRequest, ...
"""
from core.schemas import *  # noqa: F401, F403
from core.schemas import (
    HiringState, CandidateEvidence, RoleFitModel, HiringInsight,
    BiasAuditReport, AccessibilityProfile, PipelineRequest, PipelineResponse,
    SkillItem, SkillMatch, SkillGap, NDStrength, ReasoningStep,
    ShortlistResult, CandidateRank, AccessibilityMode, Recommendation,
    SkillDepth, NDWeight, FlagSeverity, IntegritySummary, IntegrityFlag,
    SignalSummary, ScoreBreakdown, RecruiterFeedbackRequest,
    RecruiterFeedbackResponse,
)
