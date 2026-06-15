from __future__ import annotations


def calculate_github_score(github_data: dict, audit_signals: dict) -> dict:
    """Compute a 0-100 GitHub score from repo activity and audit signals.

    Breakdown (100 pts total):
      - Commit consistency  : 25 pts  (low/medium/high spread)
      - Project complexity  : 25 pts  (avg complexity score across repos)
      - Domain breadth      : 20 pts  (number of distinct domains)
      - Active repo count   : 15 pts  (non-dead repos with real commits)
      - Language diversity  : 15 pts  (distinct languages used)

    Returns a dict with the score and a human-readable breakdown.
    """
    repos = github_data.get("repos", [])

    # --- commit consistency (25 pts) ---
    consistency = audit_signals.get("commit_consistency", "low")
    consistency_score = {"low": 5, "medium": 15, "high": 25}.get(consistency, 5)

    # --- project complexity (25 pts) ---
    complexity_label = audit_signals.get("project_complexity", "low")
    complexity_score = {"low": 5, "medium": 15, "high": 25}.get(complexity_label, 5)

    # --- domain breadth (20 pts) ---
    domain_breadth = audit_signals.get("domain_breadth", [])
    domain_score = min(20, len(domain_breadth) * 5)   # 5 pts per domain, max 20

    # --- active repo count (15 pts) ---
    dead_count = audit_signals.get("dead_repo_count", 0)
    active_repos = max(0, len(repos) - dead_count)
    if active_repos >= 15:
        repo_score = 15
    elif active_repos >= 8:
        repo_score = 10
    elif active_repos >= 4:
        repo_score = 7
    elif active_repos >= 1:
        repo_score = 4
    else:
        repo_score = 0

    # --- language diversity (15 pts) ---
    all_langs: set = set()
    for repo in repos:
        all_langs.update(repo.get("languages", {}).keys())
    lang_score = min(15, len(all_langs) * 3)   # 3 pts per language, max 15

    total = round(consistency_score + complexity_score + domain_score + repo_score + lang_score)

    return {
        "github_score": min(100, total),
        "github_breakdown": {
            "consistency_score": consistency_score,
            "complexity_score": complexity_score,
            "domain_score": domain_score,
            "repo_score": repo_score,
            "language_score": lang_score,
            "active_repos": active_repos,
            "distinct_languages": len(all_langs),
            "domains_detected": len(domain_breadth),
        },
    }