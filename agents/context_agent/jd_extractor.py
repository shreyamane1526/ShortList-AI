"""
agents/context_agent/jd_extractor.py  — NEW FILE

Module 1 of 3 in Context Agent.
Responsibility: parse a raw job description string into structured data.

Input:  raw JD string
Output: {"role": str, "skills": [{"name": str, "importance": float}]}

Uses Groq LLM when key is available; falls back to keyword heuristic in mock mode.
"""
from __future__ import annotations

import json
import re
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from core.config import settings

# Common tech skill → default importance weight (for heuristic fallback)
_SKILL_WEIGHTS: dict[str, float] = {
    "python":0.9,"javascript":0.9,"typescript":0.85,"java":0.9,"golang":0.85,"go":0.85,"rust":0.8,
    "react":0.8,"vue":0.75,"angular":0.75,"node":0.8,"nodejs":0.8,"nextjs":0.75,
    "fastapi":0.8,"django":0.8,"flask":0.7,"spring":0.8,"express":0.75,
    "postgresql":0.8,"mysql":0.75,"mongodb":0.75,"redis":0.7,"cassandra":0.65,
    "docker":0.75,"kubernetes":0.7,"aws":0.7,"gcp":0.65,"azure":0.65,"terraform":0.65,
    "rest":0.7,"graphql":0.65,"grpc":0.6,"api":0.6,"microservices":0.7,
    "sql":0.75,"nosql":0.6,"git":0.5,"linux":0.55,"system design":0.65,
    "machine learning":0.7,"ml":0.7,"pytorch":0.75,"tensorflow":0.75,
}

SYSTEM_PROMPT = (
    "You are a structured data extractor. "
    "Return ONLY valid JSON — no markdown, no preamble."
)

USER_PROMPT_TEMPLATE = """Extract structured data from this job description.

Return exactly this JSON shape:
{{
  "role": "job title as written in the JD",
  "skills": [
    {{"name": "skill name", "importance": 0.0_to_1.0}}
  ]
}}

importance scale:
  0.9–1.0 = must-have (explicitly required)
  0.6–0.8 = strongly preferred
  0.3–0.5 = nice-to-have / mentioned once

Job Description:
{jd}"""


def extract_jd(job_description: str) -> dict:
    """
    Returns {"role": str, "skills": [{"name": str, "importance": float}]}
    Never raises — falls back to heuristic on any failure.
    """
    if settings.use_mock:
        return _heuristic(job_description)

    prompt = USER_PROMPT_TEMPLATE.format(jd=job_description)
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        resp   = client.chat.completions.create(
            model       = settings.GROQ_MODEL,
            messages    = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature = 0,
            max_tokens  = 800,
        )
        raw   = resp.choices[0].message.content
        clean = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw).strip()
        result = json.loads(clean)
        # validate structure
        if "role" not in result or "skills" not in result:
            raise ValueError("Missing required keys")
        return result
    except Exception as e:
        print(f"  [Context/JD extractor] LLM failed ({e}) — using heuristic")
        return _heuristic(job_description)


def _heuristic(jd: str) -> dict:
    """Keyword-matching fallback. No API cost."""
    jd_lower = jd.lower()
    found = [
        {"name": skill, "importance": imp}
        for skill, imp in _SKILL_WEIGHTS.items()
        if skill in jd_lower
    ]
    first_line = jd.strip().split("\n")[0][:80].strip()
    role = first_line if len(first_line) > 5 else "Software Engineer"
    return {
        "role":   role,
        "skills": found or [{"name": "programming", "importance": 0.5}],
    }