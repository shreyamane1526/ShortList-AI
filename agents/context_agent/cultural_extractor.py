"""
agents/context_agent/cultural_extractor.py

Extracts company cultural DNA from a job description and candidate evidence.
Now supports real‑time GitHub data fetching with configurable freshness.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from core.config import settings

# -------------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

DIMENSIONS = [
    "Collaboration style",
    "Communication depth",
    "Async discipline",
    "Debate openness",
    "Documentation ethic",
]

# Company signals (from job description)
COMPANY_SIGNALS: Dict[str, Dict[str, int]] = {
    "Collaboration style": {
        "cross-functional": 20, "collaborate": 15, "team player": 15,
        "pair programming": 20, "ensemble": 15, "mob": 10,
        "independent": -15, "self-directed": -10, "solo": -10,
    },
    "Communication depth": {
        "rfc": 25, "design doc": 20, "technical writing": 20,
        "documentation": 15, "written communication": 15,
        "verbally": -5, "fast-paced": -5,
    },
    "Async discipline": {
        "remote": 20, "distributed": 20, "async": 25, "asynchronous": 25,
        "time zones": 15, "overlap": 10,
        "in-office": -20, "on-site": -15, "co-located": -10,
    },
    "Debate openness": {
        "feedback": 10, "code review": 15, "constructive": 15,
        "open culture": 20, "disagree": 15, "challenge": 10,
        "top-down": -20, "hierarchical": -15,
    },
    "Documentation ethic": {
        "documentation": 20, "wiki": 15, "runbook": 15, "readme": 10,
        "knowledge base": 15, "write-up": 10,
        "move fast": -10, "ship fast": -10,
    },
}

# Candidate signals (from GitHub activity)
CANDIDATE_SIGNALS: Dict[str, Dict[str, int]] = {
    "Collaboration style": {
        "co-authored": 20, "pair": 15, "review": 10, "thanks": 5,
    },
    "Communication depth": {
        "fix:": 5, "feat:": 5, "docs:": 20, "detailed": 15, "context:": 10,
    },
    "Async discipline": {
        "closes #": 10, "resolves #": 10, "pr": 10, "pull request": 10,
    },
    "Debate openness": {
        "refactor": 10, "improve": 10, "rethink": 15, "alternative": 15,
    },
    "Documentation ethic": {
        "readme": 20, "docs": 15, "changelog": 15, "comment": 10,
    },
}

# -------------------------------------------------------------------------
# Pydantic models for structured evidence
# -------------------------------------------------------------------------

class GitHubCommit(BaseModel):
    sha: str
    message: str
    date: datetime

class GitHubPR(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    created_at: datetime

class CandidateEvidence(BaseModel):
    github_commits: List[GitHubCommit] = Field(default_factory=list)
    github_prs: List[GitHubPR] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    last_fetched: Optional[datetime] = None

# -------------------------------------------------------------------------
# Real-time GitHub fetcher with caching
# -------------------------------------------------------------------------

class GitHubDataFetcher:
    """Fetches live candidate data from GitHub API with TTL cache."""

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache: Dict[str, tuple[CandidateEvidence, float]] = {}
        self.cache_ttl = cache_ttl_seconds
        self.client = httpx.AsyncClient(timeout=10.0)

    async def fetch_for_user(self, github_username: str, access_token: Optional[str] = None) -> CandidateEvidence:
        """Returns cached evidence if fresh, otherwise fetches from GitHub."""
        cache_key = f"{github_username}:{access_token or ''}"
        now = time.time()

        if cache_key in self.cache:
            evidence, timestamp = self.cache[cache_key]
            if now - timestamp < self.cache_ttl:
                logger.info(f"Using cached evidence for {github_username} (fresh)")
                return evidence

        logger.info(f"Fetching live GitHub data for {github_username}")
        evidence = await self._fetch_live(github_username, access_token)
        evidence.last_fetched = datetime.utcnow()
        self.cache[cache_key] = (evidence, now)
        return evidence

    async def _fetch_live(self, username: str, token: Optional[str]) -> CandidateEvidence:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            # unauthenticated -> lower rate limit, but still works
            pass

        commits = []
        prs = []

        # Fetch recent commits (last 30 days)
        try:
            resp = await self.client.get(
                f"https://api.github.com/users/{username}/events",
                headers=headers,
                params={"per_page": 50},
            )
            resp.raise_for_status()
            events = resp.json()
            for ev in events:
                if ev["type"] == "PushEvent" and "commits" in ev["payload"]:
                    for c in ev["payload"]["commits"]:
                        commits.append(GitHubCommit(
                            sha=c.get("sha", ""),
                            message=c.get("message", ""),
                            date=datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00")),
                        ))
        except Exception as e:
            logger.warning(f"Failed to fetch commits for {username}: {e}")

        # Fetch PRs authored by user
        try:
            resp = await self.client.get(
                f"https://api.github.com/search/issues",
                headers=headers,
                params={
                    "q": f"author:{username} is:pr",
                    "sort": "created",
                    "order": "desc",
                    "per_page": 20,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            for item in items:
                prs.append(GitHubPR(
                    number=item.get("number", 0),
                    title=item.get("title", ""),
                    body=item.get("body"),
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                ))
        except Exception as e:
            logger.warning(f"Failed to fetch PRs for {username}: {e}")

        return CandidateEvidence(github_commits=commits, github_prs=prs)

    async def close(self):
        await self.client.aclose()

# Global fetcher instance (reused across calls)
_github_fetcher: Optional[GitHubDataFetcher] = None

def get_github_fetcher() -> GitHubDataFetcher:
    global _github_fetcher
    if _github_fetcher is None:
        _github_fetcher = GitHubDataFetcher(cache_ttl_seconds=settings.CULTURAL_CACHE_TTL_SECONDS or 300)
    return _github_fetcher

# -------------------------------------------------------------------------
# Core scoring functions
# -------------------------------------------------------------------------

def _score_text(text: str, signals: Dict[str, int], base: int = 60) -> int:
    """Score text by keyword matching with word boundaries."""
    if not text:
        return base
    text_lower = text.lower()
    score = base
    for keyword, boost in signals.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            score += boost
    return max(0, min(100, score))

def _match_pct(candidate: int, company: int) -> int:
    """How aligned (0-100). 100 = identical."""
    diff = abs(candidate - company)
    return 100 - diff

def _build_risk_note(dimension: str, candidate: int, company: int) -> Optional[str]:
    if abs(candidate - company) < 20:
        return None
    direction = "low" if candidate < company else "high"
    hints = {
        "Collaboration style": f"Candidate leans {'solo' if direction == 'low' else 'highly collaborative'}; company expects {'team-heavy' if company > 65 else 'independent'} work.",
        "Communication depth": f"Candidate PRs tend to be {'terse' if direction == 'low' else 'verbose'}. {'Probe for written-comms experience.' if company > 65 else 'May over-document for this team.'}",
        "Async discipline": f"Async discipline gap (candidate: {candidate}, company: {company}) — {'probe for remote/distributed work experience.' if company > 65 else 'candidate may prefer more async than this team offers.'}",
        "Debate openness": f"Candidate {'rarely challenges decisions' if direction == 'low' else 'frequently pushes back'}. Verify cultural fit around feedback norms.",
        "Documentation ethic": f"Candidate's {'sparse docs' if direction == 'low' else 'heavy documentation'} may not match company's expectations.",
    }
    return hints.get(dimension)

def _evidence_to_text(evidence: CandidateEvidence | Dict[str, Any] | None) -> str:
    """Convert structured evidence into a single text blob for keyword scoring."""
    if evidence is None:
        return ""

    # Handle both dict and Pydantic model
    if isinstance(evidence, dict):
        commits = evidence.get("github_commits", [])
        prs = evidence.get("github_prs", [])
        skills = evidence.get("skills", [])
        projects = evidence.get("projects", [])
    else:
        commits = evidence.github_commits
        prs = evidence.github_prs
        skills = evidence.skills
        projects = evidence.projects

    parts = []
    for c in commits:
        if hasattr(c, "message"):
            parts.append(c.message)
        elif isinstance(c, dict):
            parts.append(c.get("message", ""))
    for pr in prs:
        if hasattr(pr, "title"):
            parts.append(pr.title)
            if pr.body:
                parts.append(pr.body)
        elif isinstance(pr, dict):
            parts.append(pr.get("title", ""))
            parts.append(pr.get("body", ""))
    for skill in skills:
        parts.append(str(skill))
    for proj in projects:
        parts.append(str(proj))

    return " ".join(parts)

# -------------------------------------------------------------------------
# LLM extraction (optional, better accuracy)
# -------------------------------------------------------------------------

SYSTEM_PROMPT = "You are a cultural alignment analyzer. Return ONLY valid JSON."

USER_PROMPT_TEMPLATE = """Analyze this job description and candidate evidence for cultural alignment.

Score each dimension 0-100 for BOTH the company (from JD) and the candidate (from GitHub activity).

Return exactly:
{{
  "overall_match_pct": <int>,
  "signal_type": "LLM + behavioral",
  "company_name": "{company_name}",
  "dimensions": [
    {{
      "dimension": "Collaboration style",
      "candidate_score": <int>,
      "company_score": <int>,
      "match_pct": <int>,
      "risk_note": <string or null>
    }},
    ... (all 5 dimensions)
  ]
}}

Job Description:
{jd}

Candidate Evidence:
{evidence_text}
"""

async def _llm_extract(jd: str, evidence_text: str, company_name: str) -> Optional[Dict]:
    """Call Groq LLM for deeper analysis; returns None on failure."""
    if not settings.GROQ_API_KEY or settings.use_mock:
        return None

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        prompt = USER_PROMPT_TEMPLATE.format(
            company_name=company_name,
            jd=jd[:4000],
            evidence_text=evidence_text[:3000],
        )
        resp = await client.chat.completions.create(
            model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content
        clean = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw).strip()
        result = json.loads(clean)
        if "dimensions" not in result or len(result["dimensions"]) != 5:
            raise ValueError("Invalid dimensions")

        # Ensure match_pct is present
        for d in result["dimensions"]:
            if "match_pct" not in d:
                d["match_pct"] = _match_pct(d["candidate_score"], d["company_score"])
            if not d.get("risk_note"):
                d["risk_note"] = _build_risk_note(d["dimension"], d["candidate_score"], d["company_score"])
        return result
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return None

# -------------------------------------------------------------------------
# Heuristic fallback
# -------------------------------------------------------------------------

def _heuristic_extract(jd: str, evidence_text: str, company_name: str) -> Dict:
    dimensions = []
    match_sums = 0
    for dim in DIMENSIONS:
        company_score = _score_text(jd, COMPANY_SIGNALS[dim], base=60)
        candidate_score = _score_text(evidence_text, CANDIDATE_SIGNALS[dim], base=65) if evidence_text else 50
        match = _match_pct(candidate_score, company_score)
        match_sums += match
        dimensions.append({
            "dimension": dim,
            "candidate_score": candidate_score,
            "company_score": company_score,
            "match_pct": match,
            "risk_note": _build_risk_note(dim, candidate_score, company_score),
        })
    overall = round(match_sums / len(DIMENSIONS))
    return {
        "overall_match_pct": overall,
        "signal_type": "Behavioral signals (heuristic)",
        "company_name": company_name,
        "dimensions": dimensions,
    }

# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------

async def extract_cultural_dna(
    job_description: str,
    evidence: Optional[CandidateEvidence | Dict[str, Any]] = None,
    company_name: str = "Company",
    github_username: Optional[str] = None,
    github_token: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict:
    """
    Extract cultural DNA.

    Args:
        job_description: The job posting text.
        evidence: Pre‑fetched candidate evidence (optional). If not provided,
                  and github_username is given, live data is fetched.
        company_name: Name of the company (for display).
        github_username: If evidence is None, fetch live for this username.
        github_token: GitHub personal access token (optional, higher rate limit).
        force_refresh: Ignore cache and fetch fresh data.

    Returns:
        Dict matching CulturalDNAData TypeScript type.
    """
    # Obtain evidence text
    final_evidence = evidence
    if final_evidence is None and github_username:
        fetcher = get_github_fetcher()
        if force_refresh:
            # Invalidate cache for this user
            cache_key = f"{github_username}:{github_token or ''}"
            fetcher.cache.pop(cache_key, None)
        final_evidence = await fetcher.fetch_for_user(github_username, github_token)

    evidence_text = _evidence_to_text(final_evidence) if final_evidence else ""

    # Try LLM first if enabled
    if not settings.use_mock and settings.GROQ_API_KEY:
        llm_result = await _llm_extract(job_description, evidence_text, company_name)
        if llm_result:
            # Fill candidate_name placeholder (caller should override)
            llm_result["candidate_name"] = ""
            return llm_result

    # Fallback to heuristic
    result = _heuristic_extract(job_description, evidence_text, company_name)
    result["candidate_name"] = ""  # to be set by caller
    return result

# -------------------------------------------------------------------------
# Convenience sync wrapper (if you need non‑async)
# -------------------------------------------------------------------------

def extract_cultural_dna_sync(
    job_description: str,
    evidence: Optional[CandidateEvidence | Dict] = None,
    company_name: str = "Company",
) -> Dict:
    """Synchronous wrapper for legacy code (uses heuristic only)."""
    evidence_text = _evidence_to_text(evidence) if evidence else ""
    return _heuristic_extract(job_description, evidence_text, company_name)

# -------------------------------------------------------------------------
# Cleanup (call at app shutdown)
# -------------------------------------------------------------------------

async def close_github_fetcher():
    if _github_fetcher:
        await _github_fetcher.close()