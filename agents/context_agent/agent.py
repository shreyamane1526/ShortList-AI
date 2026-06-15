"""
agents/context_agent/agent.py  — NEW FILE

Agent 2 — Context Agent (LangGraph node)
Orchestrates:
  1. jd_extractor  → structured role + skills from raw JD
  2. embedder      → cosine similarity matching (candidate skills vs JD skills)
  3. ChromaDB      → stores JD embedding for Ranking Agent retrieval

Writes HiringState.role_fit (RoleFitModel).
"""
from __future__ import annotations

import hashlib
import core.root  # ensures project root is on sys.path
from typing import List

from core.config  import settings
from core.schemas import (
    HiringState, RoleFitModel, SkillMatch, CandidateEvidence,
)
from .jd_extractor import extract_jd
from .embedder     import embed, store_jd_embedding, match_skills
from core.skill_mapper import normalize_skills



# ── LangGraph node ─────────────────────────────────────────────────────────────

def context_agent_node(state: dict) -> dict:
    """
    Reads: HiringState.evidence + HiringState.job_description
    Writes: HiringState.role_fit
    """
    hiring_state = HiringState(**state)
    jd           = hiring_state.job_description.strip()

    print(f"\n[Agent 2 — Context] JD preview: {jd[:60]}...")

    if not jd:
        err = "context_agent: job_description is empty"
        print(f"  ERROR: {err}")
        return {"errors": hiring_state.errors + [err]}

    if hiring_state.evidence is None:
        err = "context_agent: evidence is None — Agent 1 must run first"
        print(f"  ERROR: {err}")
        return {"errors": hiring_state.errors + [err]}

    try:
        role_fit = _build_role_fit(hiring_state, jd)
        req_matched = sum(1 for s in role_fit.required_skills_matched if s.matched)
        print(f"  Role             : {role_fit.job_title}")
        print(f"  Required matched : {req_matched}/{len(role_fit.required_skills_matched)}")
        print(f"  Overall fit      : {role_fit.overall_fit_score:.0%}")
        return {"role_fit": role_fit.model_dump()}
    except Exception as e:
        err = f"context_agent: {e}"
        print(f"  ERROR: {err}")
        return {"errors": hiring_state.errors + [err]}


# ── Core logic ─────────────────────────────────────────────────────────────────

def _build_role_fit(state: HiringState, jd: str) -> RoleFitModel:
    # Step 1 — extract structured JD data
    jd_data    = extract_jd(jd)
    role       = jd_data.get("role", "Software Engineer")
    jd_skills = jd_data.get("skills", [])

# 🔥 HARD FALLBACK (VERY IMPORTANT)
    if not jd_skills:
        jd_skills = [
            {"name": "python", "importance": 1.0},
            {"name": "fastapi", "importance": 1.0},
            {"name": "django", "importance": 1.0},
            {"name": "postgresql", "importance": 1.0},
            {"name": "mysql", "importance": 1.0},
            {"name": "docker", "importance": 0.7},
            {"name": "kubernetes", "importance": 0.7},
            {"name": "rest api", "importance": 1.0},
            {"name": "system design", "importance": 0.7},
        ]
    print(f"  DEBUG JD skills: {[s['name'] for s in jd_skills]}")

    

    skill_names  = [s["name"] for s in jd_skills]
    importance   = {s["name"]: float(s.get("importance", 0.5)) for s in jd_skills}

    # Step 2 — get candidate skills from Agent 1 output
    evidence = (CandidateEvidence(**state.evidence)
                if isinstance(state.evidence, dict) else state.evidence)

    # Original candidate skills
    raw_cand_skills = [s.name for s in evidence.skills]

    # 🔥 NORMALIZE candidate + JD skills
    cand_skill_names = list(normalize_skills(raw_cand_skills))
    skill_names = list(normalize_skills(skill_names))

# 🔥 FIX: build normalized evidence map
    cand_evidence_map = {}

    for s in evidence.skills:
        normalized = normalize_skills([s.name])
        for norm in normalized:
            cand_evidence_map.setdefault(norm, []).extend(s.evidence)

    # Step 3 — cosine similarity matching (JD skills vs candidate skills)
    matches = match_skills(skill_names, cand_skill_names)
    for jd_skill, best, score in matches:
        print(f"    [Match] {jd_skill} ↔ {best} = {score}")
    # matches: [(jd_skill, best_cand_skill, score), ...]

    # Step 4 — build SkillMatch objects
    skill_matches: List[SkillMatch] = []
    for jd_skill, best_match, score in matches:
        imp     = importance.get(jd_skill, 0.5)
        matched = score >= settings.MATCH_THRESHOLD
        skill_matches.append(SkillMatch(
            skill_name         = jd_skill,
            required = jd_skill in [
    "python",
    "fastapi",
    "django",
    "postgresql",
    "mysql",
    "rest api",
    "backend",
    "docker",
    "system design",
],  # 🔥 HARDCODED REQUIRED SKILLS (for testing) — ideally from JD extractor
            match_score        = score,
            matched            = matched,
            importance         = imp,
            candidate_evidence = cand_evidence_map.get(best_match, []),
        ))

    required_matches  = [m for m in skill_matches if m.required]
    preferred_matches = [m for m in skill_matches if not m.required]

    # Step 5 — overall fit score (based on REQUIRED skill coverage)

    required_total = len(required_matches)
    required_matched = sum(1 for m in required_matches if m.matched)

    overall_fit = required_matched / max(required_total, 1)

    # Step 6 — store JD embedding in ChromaDB for Ranking Agent retrieval
    jd_id = hashlib.md5(jd.encode()).hexdigest()[:16]
    try:
        store_jd_embedding(jd_id, jd, role, skill_names)
    except Exception as e:
        print(f"  [Context] ChromaDB store warning: {e}")

    # Step 7 — one-sentence summary
    summary = _summarise(jd, role, skill_names)

    return RoleFitModel(
        job_title                = role,
        job_description_raw      = jd,
        job_description_summary  = summary,
        required_skills_matched  = required_matches,
        preferred_skills_matched = preferred_matches,
        overall_fit_score        = overall_fit,
        domains_required         = _infer_domains(skill_names),
        jd_embedding_id          = jd_id,
    )


def _summarise(jd: str, role: str, skills: List[str]) -> str:
    if settings.use_mock or not skills:
        return f"{role} requiring {', '.join(skills[:4])}."
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        resp   = client.chat.completions.create(
            model=settings.GROQ_MODEL, temperature=0, max_tokens=60,
            messages=[{"role":"user","content":f"Summarise this job description in one sentence:\n{jd[:400]}"}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"{role} requiring {', '.join(skills[:4])}."


def _infer_domains(skill_names: List[str]) -> List[str]:
    lower = {s.lower() for s in skill_names}
    domain_map = {
        "frontend": {"react","vue","angular","javascript","typescript","html","css"},
        "backend":  {"python","java","go","golang","node","nodejs","fastapi","django","flask","spring"},
        "data":     {"sql","postgresql","mysql","mongodb","redis","kafka","spark"},
        "devops":   {"docker","kubernetes","aws","gcp","azure","terraform"},
        "mobile":   {"swift","kotlin","flutter","dart"},
    }
    return [d for d, kws in domain_map.items() if lower & kws] or ["general"]