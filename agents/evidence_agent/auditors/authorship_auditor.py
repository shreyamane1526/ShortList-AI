from __future__ import annotations

from typing import Dict, List


def audit_authorship(repos: list, github_username: str) -> dict:
    """Check whether commit author emails are consistent with the account owner.

    A genuine repo owner's commits will mostly use the same email(s). Repos
    where all commits come from unrelated email domains (and none match the
    username pattern) suggest the repo was cloned or contributed-to, not
    authored. This is a soft signal — open-source contributors will have
    diverse emails, which is fine.
    """
    flagged_repos: List[str] = []
    details: Dict[str, dict] = {}

    username_lower = github_username.lower()

    for repo in repos:
        name = repo.get("name", "unknown")
        emails: List[str] = repo.get("commit_author_emails", [])

        if not emails:
            continue

        clean_emails = [e.lower() for e in emails if e and "@" not in ("noreply.github.com",)]
        if not clean_emails:
            continue

        # count emails that contain the username or are github noreply addresses
        owner_like = sum(
            1 for e in clean_emails
            if username_lower in e
            or "noreply" in e
            or "github" in e
        )

        owner_ratio = owner_like / len(clean_emails)
        details[name] = {
            "total_commits_checked": len(clean_emails),
            "owner_ratio": round(owner_ratio, 2),
        }

        # flag only if ratio is very low AND there are enough commits to be meaningful
        if owner_ratio < 0.1 and len(clean_emails) >= 5:
            flagged_repos.append(name)

    return {
        "flagged_repos": flagged_repos,
        "authorship_details": details,
        "mismatch_detected": len(flagged_repos) > 0,
    }