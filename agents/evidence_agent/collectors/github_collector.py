"""UNCHANGED from original Agent 1 — only settings import updated."""
from __future__ import annotations
import asyncio
import sys, os
from typing import Any, Dict, List

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from core.config import settings
from .base import BaseCollector

CODE_EXTENSIONS = {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".rb", ".rs"}


class GithubCollector(BaseCollector):
    platform_name = "github"

    async def collect(self, username: str) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(
                    f"{settings.GITHUB_BASE_URL}/users/{username}/repos",
                    params={"per_page": 30, "sort": "updated"},
                    headers=settings.github_headers,
                )
                resp.raise_for_status()
                all_repos = resp.json()
            except httpx.HTTPStatusError as e:
                return {"error": f"GitHub API {e.response.status_code}", "repos": [], "total_repos": 0}
            except Exception as e:
                return {"error": str(e), "repos": [], "total_repos": 0}

            account_created = None
            try:
                await asyncio.sleep(settings.GITHUB_REQUEST_DELAY)
                r = await client.get(f"{settings.GITHUB_BASE_URL}/users/{username}", headers=settings.github_headers)
                if r.status_code == 200:
                    account_created = r.json().get("created_at")
            except Exception:
                pass

            repos_data: List[Dict[str, Any]] = []
            for repo in all_repos:
                if repo.get("fork"):
                    continue
                name  = repo["name"]
                owner = repo["owner"]["login"]
                commits      = await _fetch_commits(client, owner, name)
                await asyncio.sleep(settings.GITHUB_REQUEST_DELAY)
                languages    = await _fetch_languages(client, owner, name)
                await asyncio.sleep(settings.GITHUB_REQUEST_DELAY)
                code_samples = await _fetch_code_samples(client, owner, name)
                await asyncio.sleep(settings.GITHUB_REQUEST_DELAY)
                repos_data.append({
                    "name": name, "description": repo.get("description") or "",
                    "created_at": repo.get("created_at", ""), "updated_at": repo.get("updated_at", ""),
                    "languages": languages, "commit_count": commits["count"],
                    "commit_dates": commits["dates"], "commit_messages": commits["messages"],
                    "commit_author_emails": commits["author_emails"], "code_samples": code_samples,
                })

            return {"repos": repos_data, "total_repos": len(repos_data), "account_created": account_created}


async def _fetch_commits(client, owner, repo):
    try:
        resp = await client.get(f"{settings.GITHUB_BASE_URL}/repos/{owner}/{repo}/commits",
                                params={"per_page": 100}, headers=settings.github_headers)
        if resp.status_code != 200:
            return {"count": 0, "dates": [], "messages": [], "author_emails": []}
        commits = resp.json()
        dates, messages, emails = [], [], []
        for c in commits:
            obj = c.get("commit", {}); author = obj.get("author") or {}
            dates.append(author.get("date", ""))
            messages.append(obj.get("message", "")[:200])
            emails.append(author.get("email", ""))
        return {"count": len(commits), "dates": dates, "messages": messages, "author_emails": emails}
    except Exception:
        return {"count": 0, "dates": [], "messages": [], "author_emails": []}


async def _fetch_languages(client, owner, repo):
    try:
        resp = await client.get(f"{settings.GITHUB_BASE_URL}/repos/{owner}/{repo}/languages",
                                headers=settings.github_headers)
        return resp.json() if resp.status_code == 200 else {}
    except Exception:
        return {}


async def _fetch_code_samples(client, owner, repo):
    samples = []
    try:
        resp = await client.get(f"{settings.GITHUB_BASE_URL}/repos/{owner}/{repo}/contents/",
                                headers=settings.github_headers)
        if resp.status_code != 200:
            return samples
        contents = resp.json()
        if not isinstance(contents, list):
            return samples
        for item in contents:
            if len(samples) >= 3:
                break
            if item.get("type") != "file":
                continue
            name = item.get("name", "")
            ext  = ("." + name.rsplit(".", 1)[-1]) if "." in name else ""
            if ext.lower() not in CODE_EXTENSIONS:
                continue
            dl = item.get("download_url")
            if not dl:
                continue
            await asyncio.sleep(settings.GITHUB_REQUEST_DELAY)
            try:
                raw = await client.get(dl, headers=settings.github_headers)
                if raw.status_code == 200:
                    samples.append(raw.text[:3000])
            except Exception:
                continue
    except Exception:
        pass
    return samples