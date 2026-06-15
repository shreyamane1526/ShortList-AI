"""LeetCode collector — unchanged from Agent 1."""
from __future__ import annotations
import httpx
from .base import BaseCollector

QUERY = """
query getUserStats($username: String!) {
  matchedUser(username: $username) {
    submitStats { acSubmissionNum { difficulty count } }
    badges { name }
    profile { ranking }
  }
}
"""


class LeetcodeCollector(BaseCollector):
    platform_name = "leetcode"

    async def collect(self, username: str) -> dict:
        payload = {"query": QUERY, "variables": {"username": username}}
        headers = {"Content-Type": "application/json", "Referer": "https://leetcode.com",
                   "User-Agent": "Mozilla/5.0"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post("https://leetcode.com/graphql", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"LeetCode API {e.response.status_code}", "not_found": False}
        except Exception as e:
            return {"error": str(e), "not_found": False}

        matched = data.get("data", {}).get("matchedUser")
        if not matched:
            return {"not_found": True}

        counts  = {e["difficulty"]: e["count"] for e in matched.get("submitStats", {}).get("acSubmissionNum", [])}
        badges  = [b["name"] for b in matched.get("badges", [])]
        ranking = matched.get("profile", {}).get("ranking", 0)
        return {
            "easy_solved": counts.get("Easy", 0), "medium_solved": counts.get("Medium", 0),
            "hard_solved": counts.get("Hard", 0), "total_solved": counts.get("All", 0),
            "ranking": ranking, "badges": badges, "not_found": False,
        }