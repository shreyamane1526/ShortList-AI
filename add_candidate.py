"""
add_candidate.py — Add a single candidate to the database for a specific job description

HOW TO USE:
1. Run: python add_candidate.py --github <username> --leetcode <username> --jd "Job Description"
2. It will evaluate the candidate and save their ranking score to the DB

What it does:
  - Runs the full pipeline (Agents 1-3) for the candidate
  - Computes the ranking score
  - Saves the score to the database for the given JD
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from core.config import settings
from core.database import init_db, save_score, compute_jd_hash, get_score
from core.schemas import PipelineRequest, AccessibilityMode
from pipeline import run_pipeline
from agents.ranking_agent.scorer import compute_score


def main():
    parser = argparse.ArgumentParser(description="Add a candidate to the database")
    parser.add_argument("--github", required=True, help="GitHub username")
    parser.add_argument("--leetcode", default="", help="LeetCode username")
    parser.add_argument("--jd", required=True, help="Job description")
    parser.add_argument("--mode", default="standard", choices=["standard", "adhd", "dyslexia", "autism"], help="Accessibility mode")
    args = parser.parse_args()

    jd_hash = compute_jd_hash(args.jd)
    candidate_id = f"cand_{args.github}"

    settings.validate_and_print()
    init_db()

    print(f"\n{'═'*60}")
    print(f"  ADDING CANDIDATE TO DB")
    print(f"  GitHub: {args.github}")
    print(f"  LeetCode: {args.leetcode}")
    print(f"  JD Hash: {jd_hash[:16]}...")
    print(f"{'═'*60}")

    # Check if already exists
    existing = get_score(jd_hash, candidate_id)
    if existing:
        print(f"  Candidate already exists in DB with score {existing['composite_score']}/100")
        return

    # Run pipeline
    request = PipelineRequest(
        candidate_id=candidate_id,
        github_username=args.github,
        job_description=args.jd,
        leetcode_username=args.leetcode,
        accessibility_mode=AccessibilityMode(args.mode),
    )

    print("  Running pipeline (Agents 1-3)...")
    response = run_pipeline(request, include_ranking=False)

    if response.errors:
        print(f"  Errors: {response.errors}")
        return

    # Build evidence/role_fit/insight for ranking
    evidence = {
        "candidate_id": candidate_id,
        "github_username": args.github,
        "integrity": {
            "trust_score": response.trust_score or 50,
        },
        "nd_flags": [],
    }

    role_fit = {
        "overall_fit_score": response.overall_fit_score or 0.0,
        "job_title": "Developer",
    }

    insight = {
        "score": response.score or 0,
        "recommendation": response.recommendation or "no",
        "strengths": response.strengths or [],
        "skill_gaps": response.skill_gaps or [],
        "nd_strengths": response.nd_strengths or [],
    }

    # Compute score
    score_dict = compute_score(evidence, role_fit, insight)

    # Save to DB
    save_score(jd_hash, candidate_id, args.github, args.leetcode, score_dict)

    print(f"  ✓ Saved to DB: {score_dict['composite_score']}/100 ({score_dict['tier']}) - {score_dict['status']}")
    print(f"  Rationale: {score_dict['rationale']}")


if __name__ == "__main__":
    main()