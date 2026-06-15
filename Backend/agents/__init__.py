"""
Background enrichment agents.

Four agents run in parallel:
  1. github_agent    – repos, stars, top languages
  2. leetcode_agent  – easy/medium/hard solved, rating
  3. resume_parser_agent – skills + years from uploaded resume text
  4. job_match_agent – top 3 scraped jobs matched to candidate skills (runs last)

`enrich_candidate_async` fires agents 1-3 in parallel, then runs 4 after,
and writes per-agent status back to the DB so the frontend can show live progress.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)


# ── Cross-package import helper ──────────────────────────────────────────────
# Backend/agents/ shadows the root agents/ package.  When code in Backend/ does
#   from agents.context_agent import ...
# Python resolves `agents` to *this* package (Backend/agents/) which has no
# `context_agent` sub-package.  This helper loads the module by direct file
# path so the root agents/ package is used instead.
def _import_root_agents_module(module_rel_path: str) -> Any:
    """Import a module from the root ``agents/`` package by file path.

    ``module_rel_path`` is the dotted path relative to ``agents/``, e.g.
    ``"context_agent.cultural_extractor"``.  Returns the loaded module.
    """
    import importlib.util
    from pathlib import Path

    _root = Path(__file__).resolve().parents[2]  # project root
    _module_file = _root / "agents" / module_rel_path.replace(".", "/")
    # try .py first, then /__init__.py
    _py_path = str(_module_file.with_suffix(".py"))
    _init_path = str(_module_file / "__init__.py")

    _target = _py_path if Path(_py_path).is_file() else _init_path
    _mod_name = f"root_agents.{module_rel_path}"
    _spec = importlib.util.spec_from_file_location(_mod_name, _target)
    if _spec is None:
        raise ModuleNotFoundError(
            f"Cannot find root agents/{module_rel_path} at {_target}"
        )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
    return _mod


# Read once at import time; can be overridden by setting GITHUB_TOKEN in the environment.
_GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# ─────────────────────────────────────────────────────────────────────────────
# Individual agents
# ─────────────────────────────────────────────────────────────────────────────

def github_agent(username: str) -> dict[str, Any]:
    """Fetch public repos with full detail: count, stars, forks, languages, repo list.

    Authenticated requests get 5,000 req/hour instead of 60/hour.
    Set GITHUB_TOKEN in your environment (or Backend/.env) to enable auth.
    """
    if not username:
        return {}
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = _GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"
        else:
            logger.warning(
                "github_agent: GITHUB_TOKEN not set — using unauthenticated requests "
                "(60 req/hour limit). Set GITHUB_TOKEN in Backend/.env to raise this to 5,000/hour."
            )

        resp = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "type": "owner", "sort": "updated"},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 401:
            return {"error": "GitHub token is invalid or expired. Check GITHUB_TOKEN in Backend/.env"}
        if resp.status_code == 403:
            reset_ts = resp.headers.get("X-RateLimit-Reset", "")
            return {"error": f"GitHub rate limit exceeded. Resets at Unix timestamp {reset_ts}. Set GITHUB_TOKEN to get 5,000 req/hour."}
        if resp.status_code == 404:
            return {"error": f"GitHub user '{username}' not found"}
        resp.raise_for_status()
        repos = resp.json()

        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)
        lang_counts: dict[str, int] = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        top_languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:5]  # type: ignore[arg-type]

        # Build a clean repo list (top 20 by stars, then recency)
        sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
        repos_data = [
            {
                "name": r.get("name", ""),
                "description": (r.get("description") or "")[:200],
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "url": r.get("html_url", ""),
                "updated_at": r.get("updated_at", ""),
                "topics": r.get("topics", []),
            }
            for r in sorted_repos[:20]
        ]

        return {
            "github_repos": len(repos),
            "github_stars": total_stars,
            "github_forks": total_forks,
            "github_top_languages": top_languages,
            "github_repos_data": repos_data,
        }
    except Exception as exc:
        logger.warning("GitHub agent error for %s: %s", username, exc)
        return {"error": str(exc)}


def leetcode_agent(username: str) -> dict[str, Any]:
    """Fetch solved problem counts from LeetCode's public GraphQL API.

    LeetCode's endpoint is rate-limited and occasionally returns 403/429.
    We retry up to 2 times with a short backoff before giving up.
    """
    if not username:
        return {}
    query = """
    query userProfile($username: String!) {
      matchedUser(username: $username) {
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        profile { ranking }
      }
    }
    """
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            if attempt > 0:
                import time
                time.sleep(2 ** attempt)   # 2s, 4s backoff

            resp = requests.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"username": username}},
                headers={
                    "Content-Type": "application/json",
                    "Referer": "https://leetcode.com",
                    "User-Agent": "Mozilla/5.0 (compatible; ShortlistAI/1.0)",
                },
                timeout=20,
            )

            if resp.status_code in (403, 429):
                logger.warning(
                    "LeetCode returned %d for %s (attempt %d/3)",
                    resp.status_code, username, attempt + 1,
                )
                last_exc = Exception(f"HTTP {resp.status_code}")
                continue

            resp.raise_for_status()
            data = resp.json()
            user = (data.get("data") or {}).get("matchedUser")
            if not user:
                return {"error": f"LeetCode user '{username}' not found"}

            counts = {
                item["difficulty"]: item["count"]
                for item in user.get("submitStats", {}).get("acSubmissionNum", [])
            }
            ranking = (user.get("profile") or {}).get("ranking") or 0
            rating = max(0.0, round(3000 - (ranking / 1000), 1)) if ranking else 0.0

            return {
                "lc_easy":   counts.get("Easy", 0),
                "lc_medium": counts.get("Medium", 0),
                "lc_hard":   counts.get("Hard", 0),
                "lc_rating": rating,
            }
        except Exception as exc:
            last_exc = exc
            logger.warning("LeetCode agent error for %s (attempt %d/3): %s", username, attempt + 1, exc)

    return {"error": f"LeetCode unavailable after 3 attempts: {last_exc}"}


# Keyword lists for resume parsing
_SKILL_KEYWORDS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby", "php",
    "react", "vue", "angular", "next.js", "node.js", "express", "django", "flask", "fastapi",
    "spring", "rails", "laravel",
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd", "github actions",
    "machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn", "pandas",
    "numpy", "sql", "graphql", "rest", "grpc", "kafka", "rabbitmq",
    "html", "css", "tailwind", "sass", "webpack", "vite",
    "git", "linux", "bash", "agile", "scrum",
]

_YEAR_PATTERNS = [
    re.compile(r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience", re.I),
    re.compile(r"experience\s+(?:of\s+)?(\d+)\+?\s*years?", re.I),
]

# Section headers that typically precede a projects list
_PROJECT_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:projects?|personal\s+projects?|side\s+projects?|notable\s+projects?|"
    r"open[\s-]source|portfolio|work\s+samples?)\s*[:\-–—]?\s*\n",
    re.I,
)

# A project entry: a line that looks like a title (short, possibly followed by | or –)
_PROJECT_TITLE_RE = re.compile(
    r"^(?P<name>[A-Z][^\n]{3,60}?)(?:\s*[|–—·]\s*(?P<desc>[^\n]{0,200}))?$",
    re.M,
)


def _extract_projects_from_text(text: str) -> list[dict[str, str]]:
    """
    Heuristic project extraction from resume text.
    Looks for a "Projects" section header, then extracts title + optional description lines.
    Returns up to 8 projects as [{name, description}].
    """
    projects: list[dict[str, str]] = []

    # Try to find a projects section
    m = _PROJECT_SECTION_RE.search(text)
    if m:
        section_text = text[m.end():]
        # Stop at the next major section header (all-caps line or known section names)
        next_section = re.search(
            r"\n\s*(?:[A-Z][A-Z\s]{4,}|experience|education|skills|certifications|awards)\s*[:\n]",
            section_text, re.I,
        )
        if next_section:
            section_text = section_text[: next_section.start()]

        for line in section_text.splitlines():
            line = line.strip()
            if not line or len(line) < 4:
                continue
            # Skip lines that look like bullet points with no title
            if line.startswith(("•", "-", "*", "·")) and len(line) < 10:
                continue
            tm = _PROJECT_TITLE_RE.match(line)
            if tm:
                projects.append({
                    "name": tm.group("name").strip(),
                    "description": (tm.group("desc") or "").strip(),
                })
            if len(projects) >= 8:
                break

    # Fallback: look for lines with "built", "developed", "created" + a noun phrase
    if not projects:
        action_re = re.compile(
            r"(?:built|developed|created|designed|implemented|wrote)\s+(?:a\s+|an\s+)?([A-Z][^\n.]{5,60})",
            re.I,
        )
        for m2 in action_re.finditer(text):
            name = m2.group(1).strip().rstrip(".,;")
            if name and len(name) > 5:
                projects.append({"name": name, "description": ""})
            if len(projects) >= 5:
                break

    return projects


def resume_parser_agent(text: str) -> dict[str, Any]:
    """
    Extract skills, years of experience, and projects from plain resume text.
    Uses spaCy NER for better entity extraction, falls back to keyword matching.
    """
    if not text:
        return {}
    lower = text.lower()

    # ── Skills ───────────────────────────────────────────────────────────────
    found_skills = [kw for kw in _SKILL_KEYWORDS if kw in lower]
    seen: set[str] = set()
    skills: list[str] = []
    for s in found_skills:
        if s not in seen:
            seen.add(s)
            skills.append(s)

    # Try spaCy NER for additional skills
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        # Extract ORG entities that might be technologies/tools
        for ent in doc.ents:
            if ent.label_ == "ORG" and len(ent.text.strip()) > 2:
                candidate = ent.text.strip().lower()
                # Filter for tech-related ORGs
                if any(tech in candidate for tech in ["python", "java", "react", "node", "aws", "docker", "git", "sql", "api", "web", "mobile", "data", "cloud"]):
                    if candidate not in seen:
                        seen.add(candidate)
                        skills.append(candidate)
    except (ImportError, OSError) as exc:
        logger.warning("spaCy model not available, using keyword matching only: %s", exc)

    # ── Years of experience ───────────────────────────────────────────────────
    years: int | None = None
    for pat in _YEAR_PATTERNS:
        m = pat.search(text)
        if m:
            years = int(m.group(1))
            break

    # Try spaCy for experience extraction
    if years is None:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    date_text = ent.text.lower()
                    if "year" in date_text and any(char.isdigit() for char in date_text):
                        # Extract number from "X years" pattern
                        import re
                        num_match = re.search(r'(\d+)', date_text)
                        if num_match:
                            years = int(num_match.group(1))
                            break
        except (ImportError, OSError) as exc:
            logger.warning("spaCy experience extraction failed: %s", exc)

    # ── Projects ─────────────────────────────────────────────────────────────
    projects = _extract_projects_from_text(text)

    return {
        "resume_skills": skills,
        "resume_years_experience": years,
        "resume_projects": projects,
    }


def job_match_agent(candidate_skills: list[str], candidate_id: int) -> dict[str, Any]:
    """
    Agent 4: Match candidate skills against scraped jobs.
    Returns top 3 job matches with scores.
    Runs after the other three agents so it can use merged skills.
    """
    if not candidate_skills:
        return {"job_matches": []}
    try:
        # Import here to avoid circular imports at module load time
        from models import ScrapedJob
        jobs = ScrapedJob.query.filter_by(is_active=True).all()
        if not jobs:
            return {"job_matches": []}

        c_lower = {s.lower() for s in candidate_skills}
        scored = []
        for job in jobs:
            j_lower = {t.lower() for t in (job.tags or [])}
            overlap = len(c_lower & j_lower)
            score = min(100, round(overlap / max(len(j_lower), 1) * 100)) if j_lower else 0
            scored.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "score": score,
                "tags": job.tags or [],
                "url": job.url or "",
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"job_matches": scored[:3]}
    except Exception as exc:
        logger.warning("Job match agent error for candidate %d: %s", candidate_id, exc)
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def _run_enrichment(app, candidate_id: int, github_username: str, leetcode_username: str, resume_text: str) -> None:
    """
    Runs inside a background thread.
    Uses async agents for concurrent GitHub/LeetCode API calls.
    Writes per-agent status to agent_statuses JSON column.
    """
    import asyncio
    
    with app.app_context():
        from extensions import db
        from models import Candidate

        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return

        # Mark overall + per-agent as running
        initial_statuses = {
            "github":   "running" if github_username else "skipped",
            "leetcode": "running" if leetcode_username else "skipped",
            "resume":   "running" if resume_text else "skipped",
            "job_match": "pending",
        }
        candidate.enrichment_status = "running"
        candidate.agent_statuses = initial_statuses
        db.session.commit()

        results: dict[str, Any] = {}
        # Use the dict we just built — don't re-read from ORM (JSON may deserialize as string)
        agent_statuses: dict[str, str] = dict(initial_statuses)

        # ── Phase 1: run agents concurrently using asyncio ───────────────
        try:
            from agents.async_agents import run_enrichment_async
            
            # Run async agents
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_results = loop.run_until_complete(
                    run_enrichment_async(github_username, leetcode_username, resume_text)
                )
                results.update(async_results)
                
                # Update statuses based on results
                if github_username:
                    agent_statuses["github"] = "done" if "github_repos" in async_results else "error"
                if leetcode_username:
                    agent_statuses["leetcode"] = "done" if "lc_easy" in async_results else "error"
                if resume_text:
                    agent_statuses["resume"] = "done" if "resume_skills" in async_results else "error"
            finally:
                loop.close()
                
        except Exception as exc:
            logger.error("Async enrichment failed: %s", exc)
            # Mark all as error
            for key in agent_statuses:
                if agent_statuses[key] == "running":
                    agent_statuses[key] = f"error: {exc}"

        # Write phase-1 results immediately so UI can show partial data
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return

        for field, value in results.items():
            if hasattr(candidate, field):
                setattr(candidate, field, value)

        # Merge resume skills into main skills list (deduplicated)
        if results.get("resume_skills"):
            existing_skills = candidate.skills
            # Guard against JSON being returned as string from PostgreSQL
            if isinstance(existing_skills, str):
                import json as _json
                try:
                    existing_skills = _json.loads(existing_skills)
                except Exception:
                    existing_skills = []
            existing = set(existing_skills or [])
            merged = list(existing) + [s for s in results["resume_skills"] if s not in existing]
            candidate.skills = merged

        if results.get("resume_years_experience") and not candidate.years_experience:
            candidate.years_experience = results["resume_years_experience"]

        # Merge resume-extracted projects (don't overwrite manually entered ones)
        if results.get("resume_projects"):
            existing_projects = candidate.projects
            if isinstance(existing_projects, str):
                import json as _json
                try:
                    existing_projects = _json.loads(existing_projects)
                except Exception:
                    existing_projects = []
            existing_names = {p.get("name", "").lower() for p in (existing_projects or [])}
            new_projects = [
                p for p in results["resume_projects"]
                if p.get("name", "").lower() not in existing_names
            ]
            candidate.projects = list(existing_projects or []) + new_projects

        candidate.agent_statuses = {**agent_statuses, "job_match": "running"}
        db.session.commit()

        # ── Phase 2: job match agent (uses merged skills) ─────────────────
        all_skills = list({*(candidate.skills or []), *(results.get("resume_skills") or [])})
        jm_result = job_match_agent(all_skills, candidate_id)

        if "error" in jm_result:
            agent_statuses["job_match"] = f"error: {jm_result['error']}"
        else:
            results.update(jm_result)
            agent_statuses["job_match"] = "done"

        # ── Final write ───────────────────────────────────────────────────
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return

        if results.get("job_matches") is not None:
            candidate.top_job_matches = results["job_matches"]

        errors = [v for v in agent_statuses.values() if v.startswith("error")]
        candidate.enrichment_status = "done" if not errors else "partial"
        candidate.enrichment_error  = "; ".join(errors) if errors else None
        candidate.agent_statuses    = agent_statuses
        candidate.enriched_at       = datetime.now(timezone.utc)
        db.session.commit()
        logger.info("Enrichment complete for candidate %d — agents: %s", candidate_id, agent_statuses)


def enrich_candidate_async(app, candidate_id: int, github_username: str = "",
                           leetcode_username: str = "", resume_text: str = "") -> None:
    """Fire-and-forget: launch enrichment in a daemon thread."""
    t = threading.Thread(
        target=_run_enrichment,
        args=(app, candidate_id, github_username, leetcode_username, resume_text),
        daemon=True,
    )
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# Job-specific evaluation pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _groq_evaluate(candidate, job) -> dict[str, Any]:
    """
    Use Groq LLM to evaluate a candidate against a job description.
    Raises ValueError if GROQ_API_KEY is not set (no mock fallbacks).
    """
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise ValueError(
            "GROQ_API_KEY is required for candidate evaluation. "
            "Set it in Backend/.env to enable AI-powered matching. "
            "Get your free API key at: https://console.groq.com"
        )

    last_exc = None
    for attempt in range(3):
        try:
            from groq import Groq  # type: ignore
            client = Groq(api_key=groq_key)

            candidate_skills = list({*(candidate.skills or []), *(candidate.resume_skills or [])})
            github_summary = ""
            if candidate.github_repos:
                github_summary = (
                    f"GitHub: {candidate.github_repos} repos, {candidate.github_stars or 0} stars, "
                    f"top languages: {', '.join(candidate.github_top_languages or [])}. "
                )
            lc_summary = ""
            if candidate.lc_easy is not None:
                lc_summary = (
                    f"LeetCode: {candidate.lc_easy} easy, {candidate.lc_medium or 0} medium, "
                    f"{candidate.lc_hard or 0} hard solved. "
                )

            prompt = f"""You are an expert technical recruiter. Evaluate the following candidate against the job description.

JOB TITLE: {job.title}
JOB DESCRIPTION: {(job.description or '')[:1000]}
REQUIRED SKILLS: {', '.join(job.skills_required or [])}

CANDIDATE PROFILE:
- Name: {candidate.user.full_name if candidate.user else 'Unknown'}
- Headline: {candidate.headline or 'N/A'}
- Years of experience: {candidate.years_experience or 'Unknown'}
- Skills: {', '.join(candidate_skills[:30])}
- {github_summary}{lc_summary}
- Summary: {(candidate.summary or '')[:300]}

Respond with a JSON object (no markdown, no explanation, just raw JSON) with these exact keys:
{{
  "score": <integer 0-100>,
  "recommendation": "<YES or NO>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "why_fit": "<2-3 sentence explanation>"
}}"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            import json
            parsed = json.loads(raw)
            base_result = {
                "score": float(max(0, min(100, int(parsed.get("score", 50))))),
                "recommendation": "YES" if str(parsed.get("recommendation", "NO")).upper() == "YES" else "NO",
                "strengths": [str(s) for s in (parsed.get("strengths") or [])[:6]],
                "gaps": [str(g) for g in (parsed.get("gaps") or [])[:6]],
                "why_fit": str(parsed.get("why_fit", "")),
            }

            try:
                from agents.context_agent.cultural_extractor import extract_cultural_dna
            except ModuleNotFoundError:
                logger.warning(
                    "agents.context_agent not found via normal import "
                    "(Backend/agents/ shadows root agents/) — loading via direct path"
                )
                _mod = _import_root_agents_module("context_agent.cultural_extractor")
                extract_cultural_dna = _mod.extract_cultural_dna
            except Exception as import_err:
                logger.warning(
                    "Unexpected error importing cultural_extractor: %s — trying direct path",
                    import_err,
                )
                _mod = _import_root_agents_module("context_agent.cultural_extractor")
                extract_cultural_dna = _mod.extract_cultural_dna

            try:
                cultural_dna = extract_cultural_dna(
                    job_description=(job.description or "") + " " + " ".join(job.skills_required or []),
                    evidence=None,
                    company_name=job.company or "Company",
                )
                cultural_dna["candidate_name"] = candidate.user.full_name if candidate.user else ""
                base_result["cultural_dna"] = cultural_dna
            except Exception as cdna_err:
                logger.warning("Cultural DNA extraction failed: %s", cdna_err)
                base_result["cultural_dna"] = {}

            return base_result
        except Exception as exc:
            last_exc = exc
            logger.warning("Groq evaluation failed attempt %d/3: %s", attempt + 1, exc)
            import time
            time.sleep(1.5 * (attempt + 1))

    raise ValueError(f"AI evaluation failed after retries: {last_exc}. Check GROQ_API_KEY and try again.")

def _inclusion_enabled_for_job(job) -> bool:
    settings = getattr(job, "inclusion_settings", None) or {}
    if settings.get("enabled") is False:
        return False
    try:
        from flask import current_app
        return current_app.config.get("INCLUSION_ENABLED", True) is not False
    except Exception:
        return True


def _self_declared_nd_report(candidate) -> dict[str, Any] | None:
    if getattr(candidate, "neurodivergent", None) is not True:
        return None
    nd_type = (getattr(candidate, "nd_type", None) or "unspecified").lower()
    return {
        "nd_flag": True,
        "nd_type": nd_type,
        "nd_source": "self_declared",
        "strengths_detected": [],
        "underestimation_risks": [],
        "risk_of_underestimation": "low",
        "recommended_action": "proceed",
        "penalty_reduction_weight": 0.05,
        "nd_score": 0.25,
        "task_format": nd_type if nd_type in {"adhd", "dyslexia", "autism"} else "standard",
        "nd_summary": (
            "Candidate opted into neurodiversity support. Use only for fairness "
            "adjustment and accessible feedback."
        ),
    }


def _apply_inclusion_adjustment(result: dict[str, Any], nd_inclusion: dict[str, Any] | None) -> dict[str, Any]:
    if not nd_inclusion or not nd_inclusion.get("nd_flag"):
        return result
    adjusted = dict(result)
    original_score = float(adjusted.get("score", 0))
    relief = min(float(nd_inclusion.get("penalty_reduction_weight", 0.0)), 0.20)
    adjusted["original_score"] = original_score
    adjusted["score"] = round(min(100.0, original_score + relief * (100.0 - original_score)), 2)
    adjusted["nd_inclusion"] = nd_inclusion
    return adjusted


def run_pipeline(candidate_id: int, job_id: int) -> dict[str, Any]:
    """
    Public pipeline entry point.
    Loads candidate + job from DB, runs Groq evaluation (NO FALLBACKS),
    and returns the result dict. Does NOT write to DB — the caller handles persistence.
    
    Raises:
        ValueError: If GROQ_API_KEY is missing or evaluation fails
    """
    from models import Candidate, Job  # local import to avoid circular deps at module load
    from extensions import db

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    job = db.session.get(Job, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # No fallback - will raise ValueError if GROQ_API_KEY missing.
    # ND self-ID is never sent to the LLM; support is applied after evaluation.
    result = _groq_evaluate(candidate, job)
    if _inclusion_enabled_for_job(job):
        result = _apply_inclusion_adjustment(result, _self_declared_nd_report(candidate))
    return result


def _run_job_evaluation(app, evaluation_id: int) -> None:
    """
    Runs inside a background thread. Evaluates candidate vs job and writes result.
    Now includes feedback report generation and audit logging.
    """
    import time
    start_time = time.time()
    
    with app.app_context():
        from extensions import db
        from models import CandidateJobEvaluation, FeedbackReport
        from audit_service import record_audit_log

        ev = db.session.get(CandidateJobEvaluation, evaluation_id)
        if not ev:
            return

        logger.info("Evaluation started eval_id=%s candidate_id=%s job_id=%s", evaluation_id, ev.candidate_id, ev.job_id)
        ev.eval_status = "running"
        db.session.commit()

        try:
            # Run main evaluation pipeline
            result = run_pipeline(ev.candidate_id, ev.job_id)
            ev.score = result["score"]
            ev.recommendation = result["recommendation"]
            ev.strengths = result["strengths"]
            ev.gaps = result["gaps"]
            ev.why_fit = result["why_fit"]
            ev.nd_inclusion = result.get("nd_inclusion") or {}
            ev.cultural_dna = result.get("cultural_dna") or {}
            ev.eval_status = "done"
            ev.evaluated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Create audit log for completed evaluation
            candidate_name = ev.candidate.user.full_name if ev.candidate and ev.candidate.user else "Unknown"
            job_title = ev.job.title if ev.job else "Unknown Job"
            evaluated_at = ev.evaluated_at or datetime.now(timezone.utc)
            eval_key = f"evaluation-completed:{ev.id}:{evaluated_at.isoformat()}"
            record_audit_log(
                action="evaluation_completed",
                entity_type="evaluation",
                user_id=ev.candidate.user_id if ev.candidate and ev.candidate.user else None,
                details={
                    "source_key": eval_key,
                    "evaluation_id": ev.id,
                    "candidate_name": candidate_name,
                    "job_title": job_title,
                    "score": ev.score,
                    "recommendation": ev.recommendation,
                    "strengths": ev.strengths,
                    "gaps": ev.gaps,
                },
                created_at=evaluated_at,
            )
            db.session.commit()
            
            # Generate feedback report
            try:
                from agents.feedback_agent import generate_feedback_report
                from models import Candidate, Job
                
                candidate = db.session.get(Candidate, ev.candidate_id)
                job = db.session.get(Job, ev.job_id)
                
                if candidate and job:
                    feedback_start = time.time()
                    feedback_data = generate_feedback_report(candidate, job, result)
                    feedback_time_ms = int((time.time() - feedback_start) * 1000)
                    
                    # Check if report already exists
                    existing_report = FeedbackReport.query.filter_by(evaluation_id=evaluation_id).first()
                    if existing_report:
                        # Update existing
                        existing_report.candidate_report = feedback_data["candidate_report"]
                        existing_report.recruiter_summary = feedback_data["recruiter_summary"]
                        existing_report.interview_questions = feedback_data["interview_questions"]
                        existing_report.fairness_assessment = feedback_data["fairness_assessment"]
                        existing_report.learning_resources = feedback_data.get("learning_resources", {})
                        existing_report.task_checklist = feedback_data.get("task_checklist", [])
                        existing_report.generated_at = datetime.now(timezone.utc)
                        existing_report.generation_time_ms = feedback_time_ms
                    else:
                        # Create new
                        report = FeedbackReport(
                            evaluation_id=evaluation_id,
                            candidate_report=feedback_data["candidate_report"],
                            recruiter_summary=feedback_data["recruiter_summary"],
                            interview_questions=feedback_data["interview_questions"],
                            fairness_assessment=feedback_data["fairness_assessment"],
                            learning_resources=feedback_data.get("learning_resources", {}),
                            task_checklist=feedback_data.get("task_checklist", []),
                            generation_time_ms=feedback_time_ms,
                        )
                        db.session.add(report)
                    
                    db.session.commit()
                    logger.info("Feedback report generated for evaluation %d in %dms", evaluation_id, feedback_time_ms)
            except Exception as feedback_exc:
                logger.warning("Feedback generation failed for evaluation %d: %s", evaluation_id, feedback_exc)
                # Don't fail the entire evaluation if feedback generation fails
            
        except Exception as exc:
            logger.warning("Evaluation failed eval_id=%s: %s", evaluation_id, exc)
            ev.eval_status = "error"
            ev.eval_error = str(exc)
            ev.recommendation = "PENDING"
            db.session.commit()

        total_time = time.time() - start_time
        logger.info(
            "Evaluation completed eval_id=%d in %.2fs score=%.1f rec=%s status=%s",
            evaluation_id, total_time, ev.score or 0, ev.recommendation,
            ev.eval_status,
        )


def evaluate_candidate_for_job_async(app, evaluation_id: int) -> None:
    """Fire-and-forget: evaluate a candidate against a job in a daemon thread."""
    t = threading.Thread(
        target=_run_job_evaluation,
        args=(app, evaluation_id),
        daemon=True,
    )
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# Task Status Tracking (for monitoring background jobs)
# ─────────────────────────────────────────────────────────────────────────────

_task_status: dict[int, dict[str, Any]] = {}  # eval_id -> {status, progress, error}


def get_task_status(evaluation_id: int) -> dict[str, Any]:
    """Get the current status of an evaluation task."""
    return _task_status.get(evaluation_id, {"status": "unknown", "progress": 0})
