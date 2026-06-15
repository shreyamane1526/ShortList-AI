from __future__ import annotations


# Scoring thresholds based on realistic LeetCode distributions
_EASY_MAX = 300       # 300+ easy → full easy score
_MEDIUM_MAX = 400     # 400+ medium → full medium score
_HARD_MAX = 150       # 150+ hard → full hard score

_RANKING_TIERS = [
    (1_000,   100),   # top 1k → 100
    (5_000,   95),
    (10_000,  90),
    (25_000,  80),
    (50_000,  70),
    (100_000, 55),
    (250_000, 40),
    (500_000, 25),
    (float("inf"), 10),
]


def calculate_leetcode_score(leetcode_data: dict) -> dict:
    """Compute a 0-100 LeetCode score from solved counts, ranking, and badges.

    Breakdown (100 pts total):
      - Problems solved quality  : 60 pts  (easy×0.5 + medium×1.5 + hard×4, normalized)
      - Global ranking           : 30 pts  (tiered)
      - Badges                   : 10 pts  (unique badges, capped)

    Returns a dict with the score and a human-readable breakdown.
    """
    if not leetcode_data or leetcode_data.get("not_found") or leetcode_data.get("error"):
        return {"leetcode_score": None, "leetcode_breakdown": None}

    easy   = leetcode_data.get("easy_solved", 0)
    medium = leetcode_data.get("medium_solved", 0)
    hard   = leetcode_data.get("hard_solved", 0)
    ranking = leetcode_data.get("ranking", 0) or 0
    badges  = leetcode_data.get("badges", [])

    # --- problems score (60 pts) ---
    # weighted sum: hard problems count more
    weighted = (easy * 0.5) + (medium * 1.5) + (hard * 4.0)
    # max weighted = 300*0.5 + 400*1.5 + 150*4.0 = 150 + 600 + 600 = 1350
    MAX_WEIGHTED = (_EASY_MAX * 0.5) + (_MEDIUM_MAX * 1.5) + (_HARD_MAX * 4.0)
    problem_score = min(60, round((weighted / MAX_WEIGHTED) * 60, 1))

    # --- ranking score (30 pts) ---
    rank_score = 0
    if ranking and ranking > 0:
        for threshold, pts in _RANKING_TIERS:
            if ranking <= threshold:
                rank_score = round((pts / 100) * 30, 1)
                break

    # --- badge score (10 pts) ---
    unique_badges = len(set(badges))
    badge_score = min(10, unique_badges * 2)  # 2 pts per unique badge, max 10

    total = round(problem_score + rank_score + badge_score)

    return {
        "leetcode_score": min(100, total),
        "leetcode_breakdown": {
            "problems_score": problem_score,
            "ranking_score": rank_score,
            "badge_score": badge_score,
            "easy_solved": easy,
            "medium_solved": medium,
            "hard_solved": hard,
            "global_ranking": ranking,
            "unique_badges": unique_badges,
        },
    }