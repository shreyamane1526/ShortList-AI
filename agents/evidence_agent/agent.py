"""
agents/evidence_agent/agent.py  — MODIFIED FILE

Changes from original Agent 1:
  - Wrapped as a LangGraph node function (evidence_agent_node)
  - Imports CandidateEvidence from core.schemas instead of local models.py
  - Database calls go to core.database (PostgreSQL-aware)
  - Everything else is IDENTICAL to the original Agent 1 logic
"""


from __future__ import annotations
import nest_asyncio
nest_asyncio.apply()

import core.root  # ensures project root is on sys.path (Windows + Linux safe)

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional


from core.config   import settings
from core.database import save_profile, get_profile, is_cache_valid
from core.schemas  import (
    CandidateEvidence, HiringState,
    SkillItem, SkillDepth, IntegritySummary, IntegrityFlag,
    SignalSummary, ScoreBreakdown, FlagSeverity,
)
from .collectors import GithubCollector, LeetcodeCollector, PortfolioCollector
from .auditors   import (
    audit_commits, audit_consistency, audit_similarity,
    audit_authorship, audit_account_health,
)

_github    = GithubCollector()
_leetcode  = LeetcodeCollector()
_portfolio = PortfolioCollector()


# ── LangGraph node ─────────────────────────────────────────────────────────────

def evidence_agent_node(state: dict) -> dict:
    """
    LangGraph synchronous node wrapper.
    Reads HiringState, writes HiringState.evidence (CandidateEvidence).
    Checks PostgreSQL cache first — skips re-scraping if fresh data exists.
    """
    hiring_state = HiringState(**state)
    username     = hiring_state.github_username
    # Compound cache key: include leetcode username so different combinations
    # are cached separately. "torvalds" and "torvalds+tourist" are different runs.
    cache_key = username
    if hiring_state.leetcode_username:
        cache_key = f"{username}__lc_{hiring_state.leetcode_username}"

    print(f"\n[Agent 1 — Evidence] GitHub: {username}")

    # ── cache hit ──────────────────────────────────────────────────────────────
    if is_cache_valid(cache_key):
        cached = get_profile(cache_key)
        if cached:
            print(f"  Cache hit ({cache_key}) — skipping collection")
            return {"evidence": cached}

    try:
        profile = asyncio.run(_run(hiring_state))
        save_profile(cache_key, profile.model_dump())
        print(f"  Skills: {len(profile.skills)}  Trust: {profile.integrity.trust_score}/100  Sources: {profile.sources_used}")
        return {"evidence": profile.model_dump()}
    except Exception as e:
        err = f"evidence_agent: {e}"
        print(f"  ERROR: {err}")
        # In mock mode: return a full stub profile so downstream agents can still run
        if settings.use_mock:
            print(f"  Mock mode: returning stub CandidateEvidence for pipeline continuity")
            stub = _stub_evidence(username)
            return {"evidence": stub.model_dump()}
        return {"errors": hiring_state.errors + [err]}


# ── Async pipeline ─────────────────────────────────────────────────────────────

async def _run(state: HiringState) -> CandidateEvidence:
    github_task   = asyncio.create_task(_github.collect(state.github_username))
    leetcode_task = asyncio.create_task(
        _leetcode.collect(state.leetcode_username) if state.leetcode_username else _empty()
    )
    portfolio_task = asyncio.create_task(_collect_portfolio(state))

    github_data, leetcode_data, portfolio_result = await asyncio.gather(
        github_task, leetcode_task, portfolio_task
    )

    if github_data.get("error") and not github_data.get("repos"):
        raise RuntimeError(f"GitHub failed: {github_data['error']}")

    repos = github_data.get("repos", [])

    commit_audit   = audit_commits(repos)
    consistency    = audit_consistency(repos)
    similarity     = audit_similarity(repos)
    authorship     = audit_authorship(repos, state.github_username)
    account_health = audit_account_health(repos, github_data.get("account_created"))

    trust = _trust_score(commit_audit, consistency, similarity, authorship, account_health)
    llm   = _extract_skills(github_data, leetcode_data, portfolio_result.get("text",""), trust["trust_score"])

    domain_breadth    = _infer_domains(repos)
    complexity_label  = _overall_complexity(consistency)
    gh_score          = _github_score(repos, commit_audit, complexity_label, domain_breadth, account_health)
    lc_score          = _leetcode_score(leetcode_data)
    avg               = _avg_score(gh_score.get("github_score"), lc_score.get("leetcode_score"))

    sources = ["github"]
    if leetcode_data and not leetcode_data.get("not_found") and not leetcode_data.get("error"):
        sources.append("leetcode")
    if portfolio_result.get("text"):
        sources.append(portfolio_result.get("type","portfolio"))

    return CandidateEvidence(
        candidate_id             = state.github_username,
        github_username          = state.github_username,
        collected_at             = datetime.now(timezone.utc),
        sources_used             = sources,
        skills                   = [SkillItem(**s) for s in llm.get("skills",[]) if _valid(s)],
        integrity                = IntegritySummary(
            trust_score          = trust["trust_score"],
            flags                = [IntegrityFlag(**f) for f in trust["flags"]],
        ),
        signals                  = SignalSummary(
            commit_consistency   = commit_audit["commit_consistency"],
            project_complexity   = complexity_label,
            domain_breadth       = domain_breadth,
            total_repos_analyzed = len(repos),
            leetcode_solved      = leetcode_data.get("total_solved") if leetcode_data else None,
            account_age_days     = account_health.get("account_age_days"),
            dead_repo_count      = account_health.get("dead_repo_count",0),
        ),
        scores                   = ScoreBreakdown(
            github_score         = gh_score.get("github_score"),
            github_breakdown     = gh_score.get("github_breakdown"),
            leetcode_score       = lc_score.get("leetcode_score"),
            leetcode_breakdown   = lc_score.get("leetcode_breakdown"),
            average_score        = avg,
        ),
        raw_summary              = llm.get("raw_summary",""),
        hardest_function_summary = llm.get("hardest_function_summary",""),
        portfolio_text           = portfolio_result.get("text",""),
    )


# ── LLM skill extraction ───────────────────────────────────────────────────────

def _extract_skills(github_data, leetcode_data, portfolio_text, trust_score) -> dict:
    repos = github_data.get("repos", [])

    descriptions = [r.get("description","") for r in repos if r.get("description")]
    topics = [t for r in repos for t in r.get("topics", [])]
    if settings.use_mock:
        print("  [Evidence] Mock mode — returning stub skills")
        return {"skills":[
            {"name":"Python","confidence":0.92,"depth":"production","evidence":["Primary language, 8+ repos"],"recency_days":7,"source":"github"},
            {"name":"FastAPI","confidence":0.85,"depth":"working","evidence":["REST API project with auth"],"recency_days":21,"source":"github"},
            {"name":"PostgreSQL","confidence":0.70,"depth":"working","evidence":["DB migrations in portfolio"],"recency_days":30,"source":"portfolio"},
        ],"hardest_function_summary":"Async REST API with JWT auth.","raw_summary":"Backend developer with strong Python and API skills."}

    repos     = github_data.get("repos",[])
    all_langs = {}
    for r in repos:
        for lang, b in r.get("languages",{}).items():
            all_langs[lang] = all_langs.get(lang,0)+b
    top_langs = sorted(all_langs, key=lambda l: all_langs[l], reverse=True)[:10] or ["unknown"]
    msgs      = [m for r in repos for m in r.get("commit_messages",[])][:15]
    code_parts= []
    for r in repos[:5]:
        for s in r.get("code_samples",[])[:2]:
            code_parts.append(f"--- {r['name']} ---\n{s[:800]}")
    code_block = "\n\n".join(code_parts) or "No code samples."
    lc_line = (f"{leetcode_data.get('easy_solved',0)} easy, {leetcode_data.get('medium_solved',0)} medium, {leetcode_data.get('hard_solved',0)} hard. Ranking: {leetcode_data.get('ranking','N/A')}"
               if leetcode_data and not leetcode_data.get("not_found") else "No LeetCode data.")
    prompt = f"""Analyze this developer's evidence and extract skills.

    GitHub:
    Repos: {github_data.get('total_repos',0)}
    Languages: {', '.join(top_langs) or 'unknown'}

    Repo Descriptions:
    {' '.join(descriptions[:20])}

    Topics:
    {', '.join(topics[:20])}

    Commits:
    {json.dumps(msgs)}

    Code:
    {code_block}

    LeetCode:
    {lc_line}

    Portfolio:
    {portfolio_text[:800] if portfolio_text else 'Not provided.'}

    Trust score: {trust_score}/100

    IMPORTANT:
    If a repository description contains words like "API", "backend", "service", or "server",
    you MUST infer backend-related skills.

    Return ONLY valid JSON:
    {{"skills":[{{"name":"...","confidence":0.85,"depth":"working","evidence":["..."],"recency_days":30,"source":"github"}}],"hardest_function_summary":"...","raw_summary":"..."}}

    depth: exposure|working|production
    """

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        resp   = client.chat.completions.create(
            model=settings.GROQ_MODEL, temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            messages=[{"role":"system","content":"You are a technical hiring analyst. Return valid JSON only."},
                      {"role":"user","content":prompt}],
        )
        raw   = resp.choices[0].message.content
        clean = re.sub(r"```(?:json)?\s*([\s\S]*?)```",r"\1",raw).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"  [Evidence] LLM error: {e}")
        return {"skills":[],"hardest_function_summary":"","raw_summary":""}


# ── Trust score ────────────────────────────────────────────────────────────────

def _trust_score(commit_audit, consistency, similarity, authorship, account_health) -> dict:
    """
    Trust score: 0–100, measures evidence AUTHENTICITY only.
    Not a proxy for skill — a developer can have low trust score and high skill.

    Deductions are capped per category so no single signal can dominate.
    Floor: minimum 20/100 — even flagged repos show some evidence.

    Clone risk only fires when 2+ weak signals align (see commit_auditor.py).
    Small personal repos (blogs, experiments) are common for genuine developers.
    """
    score, flags = 100, []

    # Clone risk: -10 per repo (reduced from 15), max -25 (reduced from 40)
    # Genuine developers often have small personal repos that pattern-match as clones.
    clone_repos = commit_audit.get("clone_risk_repos", [])
    clone_deduction = min(len(clone_repos) * 10, 25)
    score -= clone_deduction
    for r in clone_repos:
        flags.append({"flag_type":"clone_risk","severity":"medium",
                      "detail":f"Repo '{r}' shows low-commit + generic-message pattern"})

    # Skill jump: -15 (reduced from 20)
    if consistency.get("skill_jump_detected"):
        score -= 15
        flags.append({"flag_type":"skill_jump","severity":"medium",
                      "detail":consistency.get("jump_details","Unusual complexity jump detected")})

    # Tutorial similarity: -8 per repo, max -20
    similar = similarity.get("flagged_repos", [])
    score -= min(len(similar) * 8, 20)
    for item in similar:
        flags.append({"flag_type":"high_similarity","severity":"medium",
                      "detail":f"'{item['repo']}' matched '{item['matched_reference']}' at {item['score']*100:.0f}%"})

    # Low commit consistency: -8 (reduced from 10)
    if commit_audit.get("commit_consistency") == "low":
        score -= 8
        flags.append({"flag_type":"low_commit_consistency","severity":"low",
                      "detail":"Commit spread is low across repos"})

    # Authorship mismatch: -15 per repo, max -20
    auth_flagged = authorship.get("flagged_repos", [])
    score -= min(len(auth_flagged) * 15, 20)
    for r in auth_flagged:
        flags.append({"flag_type":"authorship_mismatch","severity":"high",
                      "detail":f"'{r}' commits mostly from unrelated email addresses"})

    # Account health: -5 (reduced from 10)
    if account_health.get("suspicious_age_ratio"):
        score -= 5
        flags.append({"flag_type":"account_health","severity":"low",
                      "detail":"New account with unusually many active repos"})

    # Global floor: minimum 20 — even flagged repos represent real evidence
    return {"trust_score": max(20, score), "flags": flags}


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _github_score(repos, commit_audit, complexity_label, domain_breadth, account_health) -> dict:
    c = {"low":5,"medium":15,"high":25}.get(commit_audit.get("commit_consistency","low"),5)
    x = {"low":5,"medium":15,"high":25}.get(complexity_label,5)
    d = min(20, len(domain_breadth)*5)
    dead   = account_health.get("dead_repo_count",0)
    active = max(0,len(repos)-dead)
    r = 15 if active>=15 else 10 if active>=8 else 7 if active>=4 else 4 if active>=1 else 0
    langs  = {lang for repo in repos for lang in repo.get("languages",{})}
    l = min(15,len(langs)*3)
    total  = min(100,c+x+d+r+l)
    return {"github_score":total,"github_breakdown":{"consistency":c,"complexity":x,"domain":d,"repos":r,"languages":l,"active_repos":active,"distinct_languages":len(langs)}}


def _leetcode_score(data) -> dict:
    if not data or data.get("not_found") or data.get("error"):
        return {"leetcode_score":None,"leetcode_breakdown":None}
    easy,medium,hard = data.get("easy_solved",0),data.get("medium_solved",0),data.get("hard_solved",0)
    ranking,badges   = data.get("ranking",0) or 0,data.get("badges",[])
    weighted = easy*0.5+medium*1.5+hard*4.0
    prob     = min(60,round(weighted/(300*0.5+400*1.5+150*4.0)*60,1))
    rank_pts = 0
    for t,pts in [(1000,100),(5000,95),(10000,90),(25000,80),(50000,70),(100000,55),(250000,40),(500000,25),(float("inf"),10)]:
        if ranking<=t: rank_pts=round(pts/100*30,1); break
    badge_pts = min(10,len(set(badges))*2)
    return {"leetcode_score":min(100,round(prob+rank_pts+badge_pts)),"leetcode_breakdown":{"problems":prob,"ranking":rank_pts,"badges":badge_pts}}


def _avg_score(gh, lc) -> Optional[int]:
    sources = [(gh,50),(lc,30)] if lc else [(gh,50)] if gh else []
    if not sources: return None
    tw = sum(w for _,w in sources)
    return round(sum(s*w for s,w in sources)/tw)


def _infer_domains(repos) -> list:
    dm = {"frontend":{"javascript","typescript","html","css","vue","svelte"},
          "backend":{"python","java","go","ruby","php","kotlin","rust"},
          "systems":{"c","c++","rust","assembly"},"mobile":{"swift","kotlin","dart"},
          "data":{"jupyter notebook","r","scala"},"devops":{"dockerfile","shell","hcl"}}
    langs = {l.lower() for r in repos for l in r.get("languages",{})}
    return [d for d,kws in dm.items() if langs&kws] or ["general"]


def _overall_complexity(consistency) -> str:
    scores = list(consistency.get("complexity_scores",{}).values())
    if not scores: return "low"
    avg = sum(scores)/len(scores)
    return "high" if avg>50 else ("medium" if avg>20 else "low")


def _valid(s) -> bool:
    return (isinstance(s.get("name"),str) and isinstance(s.get("confidence"),(int,float))
            and s.get("depth") in ("exposure","working","production")
            and isinstance(s.get("evidence"),list) and isinstance(s.get("recency_days"),int))


async def _empty(): return {}


def _stub_evidence(username: str) -> CandidateEvidence:
    """Full stub CandidateEvidence used in mock mode when GitHub is unreachable."""
    return CandidateEvidence(
        candidate_id    = username,
        github_username = username,
        sources_used    = ["github_mock"],
        skills          = [
            SkillItem(name="Python",     confidence=0.92, depth=SkillDepth.PRODUCTION,
                      evidence=["Primary language, 8+ repos"], recency_days=7,  source="github"),
            SkillItem(name="FastAPI",    confidence=0.85, depth=SkillDepth.WORKING,
                      evidence=["REST API project with auth"], recency_days=21, source="github"),
            SkillItem(name="PostgreSQL", confidence=0.70, depth=SkillDepth.WORKING,
                      evidence=["DB migrations in portfolio"], recency_days=30, source="portfolio"),
        ],
        integrity       = IntegritySummary(trust_score=85, flags=[]),
        signals         = SignalSummary(
            commit_consistency    = "high",
            project_complexity    = "high",
            domain_breadth        = ["backend", "devops"],
            total_repos_analyzed  = 8,
            dead_repo_count       = 0,
        ),
        scores          = ScoreBreakdown(github_score=78, average_score=78),
        raw_summary     = f"Mock profile for {username} — real GitHub data unavailable in mock mode.",
        hardest_function_summary = "Async REST API with JWT auth and role-based access.",
    )


async def _collect_portfolio(state: HiringState) -> dict:
    texts = []
    if state.portfolio_url:
        r = await _portfolio.collect(state.portfolio_url)
        if r.get("text"): texts.append(r["text"])
    if state.resume_url:
        r = await _portfolio.collect(state.resume_url)
        if r.get("text"): texts.append(r["text"])
    return {"type":"portfolio","text":" ".join(texts)[:5000],"error":None}