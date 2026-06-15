"""
Async agents using aiohttp for concurrent API calls.
Optimized for <15 second execution time.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Cache for API responses (simple in-memory cache)
_CACHE: dict[str, Any] = {}
_CACHE_TTL = 3600  # 1 hour


async def github_agent_async(username: str, session: aiohttp.ClientSession) -> dict[str, Any]:
    """Async GitHub agent using aiohttp."""
    if not username:
        return {}
    
    cache_key = f"github:{username}"
    if cache_key in _CACHE:
        logger.info("GitHub cache hit for %s", username)
        return _CACHE[cache_key]
    
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"
        
        async with session.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "type": "owner", "sort": "updated"},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                return {"error": "GitHub token is invalid or expired"}
            if resp.status == 403:
                return {"error": "GitHub rate limit exceeded"}
            if resp.status == 404:
                return {"error": f"GitHub user '{username}' not found"}
            
            resp.raise_for_status()
            repos = await resp.json()
        
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)
        lang_counts: dict[str, int] = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        top_languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:5]  # type: ignore
        
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
        
        result = {
            "github_repos": len(repos),
            "github_stars": total_stars,
            "github_forks": total_forks,
            "github_top_languages": top_languages,
            "github_repos_data": repos_data,
        }
        
        _CACHE[cache_key] = result
        return result
        
    except Exception as exc:
        logger.warning("GitHub agent error for %s: %s", username, exc)
        return {"error": str(exc)}


async def leetcode_agent_async(username: str, session: aiohttp.ClientSession) -> dict[str, Any]:
    """Async LeetCode agent using aiohttp."""
    if not username:
        return {}
    
    cache_key = f"leetcode:{username}"
    if cache_key in _CACHE:
        logger.info("LeetCode cache hit for %s", username)
        return _CACHE[cache_key]
    
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
    
    for attempt in range(3):
        try:
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)
            
            async with session.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"username": username}},
                headers={
                    "Content-Type": "application/json",
                    "Referer": "https://leetcode.com",
                    "User-Agent": "Mozilla/5.0 (compatible; ShortlistAI/1.0)",
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (403, 429):
                    logger.warning("LeetCode returned %d for %s (attempt %d/3)", resp.status, username, attempt + 1)
                    continue
                
                resp.raise_for_status()
                data = await resp.json()
            
            user = (data.get("data") or {}).get("matchedUser")
            if not user:
                return {"error": f"LeetCode user '{username}' not found"}
            
            counts = {
                item["difficulty"]: item["count"]
                for item in user.get("submitStats", {}).get("acSubmissionNum", [])
            }
            ranking = (user.get("profile") or {}).get("ranking") or 0
            rating = max(0.0, round(3000 - (ranking / 1000), 1)) if ranking else 0.0
            
            result = {
                "lc_easy": counts.get("Easy", 0),
                "lc_medium": counts.get("Medium", 0),
                "lc_hard": counts.get("Hard", 0),
                "lc_rating": rating,
            }
            
            _CACHE[cache_key] = result
            return result
            
        except Exception as exc:
            logger.warning("LeetCode agent error for %s (attempt %d/3): %s", username, attempt + 1, exc)
    
    return {"error": "LeetCode unavailable after 3 attempts"}


async def run_enrichment_async(
    github_username: str,
    leetcode_username: str,
    resume_text: str,
) -> dict[str, Any]:
    """
    Run GitHub and LeetCode agents concurrently using asyncio.
    Resume parsing is synchronous (CPU-bound).
    
    Returns merged results dict.
    """
    results: dict[str, Any] = {}
    
    # Run resume parser synchronously (it's CPU-bound, not I/O-bound)
    if resume_text:
        from agents import resume_parser_agent
        resume_result = resume_parser_agent(resume_text)
        if "error" not in resume_result:
            results.update(resume_result)
    
    # Run GitHub and LeetCode concurrently
    tasks = []
    async with aiohttp.ClientSession() as session:
        if github_username:
            tasks.append(("github", github_agent_async(github_username, session)))
        if leetcode_username:
            tasks.append(("leetcode", leetcode_agent_async(leetcode_username, session)))
        
        if tasks:
            task_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for (name, _), result in zip(tasks, task_results):
                if isinstance(result, Exception):
                    logger.error("%s agent failed: %s", name, result)
                elif isinstance(result, dict) and "error" not in result:
                    results.update(result)
    
    return results
