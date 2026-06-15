"""
agents/ranking_agent/llm_justifier.py

Calls Groq to write the plain-English justification for a ranking decision.
The LLM NEVER changes a score — it only writes prose.
Uses the same Groq pattern already in reasoning_agent/agent.py.
"""
from __future__ import annotations
import json
import httpx
from core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a fair, skills-first hiring analyst writing a shortlist justification.

STRICT RULES:
- Write ONLY from the data you are given. Never invent facts.
- Never mention race, gender, age, university, or career gaps.
- Acknowledge neurodivergent strengths positively if present.
- rank_justification: 2-3 sentences explaining why this rank was assigned.
- differentiator: 1 sentence — what uniquely helps or limits this candidate.

Return ONLY valid JSON (no markdown, no explanation):
{
  "rank_justification": "...",
  "differentiator": "..."
}"""


def generate_justification(rank: int, score_dict: dict,
                            insight: dict, role_fit: dict) -> tuple[str, str]:
    """
    Returns (rank_justification, differentiator).
    Falls back to the deterministic rationale if Groq is unavailable.
    """
    if settings.use_mock:
        return score_dict["rationale"], "See rationale above."

    payload = {
        "rank":             rank,
        "composite_score":  score_dict["composite_score"],
        "tier":             score_dict["tier"],
        "components":       score_dict["components"],
        "recommendation":   insight.get("recommendation"),
        "strengths":        (insight.get("strengths") or [])[:3],
        "critical_gaps":    [
            g.get("skill_name", "?")
            for g in (insight.get("skill_gaps") or [])
            if isinstance(g, dict) and g.get("severity") == "critical"
        ],
        "nd_strengths_count": score_dict["components"]["nd_strengths_count"],
        "role_fit_pct":     round(score_dict["components"]["raw_fit_score"], 1),
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model":       settings.GROQ_MODEL,
        "temperature": 0.1,
        "max_tokens":  600,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"CANDIDATE DATA:\n{json.dumps(payload, indent=2)}"},
        ],
    }
    try:
        resp = httpx.post(GROQ_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        return parsed.get("rank_justification", score_dict["rationale"]), \
               parsed.get("differentiator", "")
    except Exception as exc:
        print(f"  [Ranking LLM] Groq call failed: {exc} — using deterministic rationale")
        return score_dict["rationale"], ""
