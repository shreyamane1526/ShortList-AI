from __future__ import annotations

from datetime import datetime, timezone
from typing import List


def audit_account_health(repos: list, account_created: str | None) -> dict:
    """Assess account and repo health signals.

    Checks:
    - Dead repos: no README-like file, no description, 0 or 1 commits
    - Account age vs repo count: many polished repos on a very new account
      is a weak fabrication signal (combined with other flags)

    Account age alone is NOT a negative signal — students and career switchers
    often create GitHub accounts late. This only contributes to trust scoring
    when combined with other red flags.
    """
    dead_repos: List[str] = []

    for repo in repos:
        name = repo.get("name", "unknown")
        commit_count = repo.get("commit_count", 0)
        description = repo.get("description", "").strip()
        code_samples = repo.get("code_samples", [])

        # dead repo: basically empty — no description, no real commits, no readable code
        if commit_count <= 1 and not description and not code_samples:
            dead_repos.append(name)

    account_age_days = None
    suspicious_age_ratio = False

    if account_created:
        try:
            created_dt = datetime.fromisoformat(account_created.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            account_age_days = (now - created_dt).days

            # weak signal: account < 90 days old but already has 15+ non-dead repos
            active_repos = len(repos) - len(dead_repos)
            if account_age_days < 90 and active_repos >= 15:
                suspicious_age_ratio = True
        except Exception:
            pass

    return {
        "dead_repos": dead_repos,
        "dead_repo_count": len(dead_repos),
        "account_age_days": account_age_days,
        "suspicious_age_ratio": suspicious_age_ratio,
    }