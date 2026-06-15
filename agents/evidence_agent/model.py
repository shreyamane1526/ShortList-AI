from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CandidateInput(BaseModel):
    github_username: str
    leetcode_username: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_url: Optional[str] = None  # direct link to a PDF
    extra_profiles: Optional[Dict[str, str]] = None  # e.g. {"codeforces": "username"}


class SkillItem(BaseModel):
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    depth: str  # "exposure" | "working" | "production"
    evidence: List[str]
    recency_days: int


class IntegrityFlag(BaseModel):
    flag_type: str  # "clone_risk" | "skill_jump" | "high_similarity" | "authorship_mismatch" | "account_health"
    severity: str   # "low" | "medium" | "high"
    detail: str


class IntegritySummary(BaseModel):
    trust_score: int = Field(..., ge=0, le=100)
    flags: List[IntegrityFlag]


class ScoreBreakdown(BaseModel):
    github_score: Optional[int] = None
    github_breakdown: Optional[Dict] = None
    leetcode_score: Optional[int] = None
    leetcode_breakdown: Optional[Dict] = None
    portfolio_score: Optional[int] = None
    average_score: Optional[int] = None      # weighted average across available sources


class SignalSummary(BaseModel):
    commit_consistency: str          # "low" | "medium" | "high"
    project_complexity: str          # "low" | "medium" | "high"
    domain_breadth: List[str]        # e.g. ["frontend", "backend", "devops"]
    total_repos_analyzed: int
    leetcode_solved: Optional[int] = None
    account_age_days: Optional[int] = None
    dead_repo_count: int = 0


class SkillProfile(BaseModel):
    schema_version: str = "1.0"
    candidate_id: str                # github_username
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    sources_used: List[str]
    skills: List[SkillItem]
    integrity: IntegritySummary
    signals: SignalSummary
    scores: ScoreBreakdown           # per-source scores + weighted average
    raw_summary: str                 # one paragraph from LLM about the candidate
    hardest_function_summary: str = ""