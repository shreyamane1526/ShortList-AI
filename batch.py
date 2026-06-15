"""
batch.py — Display rankings for all candidates stored in DB for a specific job description

HOW TO USE:
1. Run: python batch.py "Your job description here"
2. It will show all stored rankings for that JD

What it does:
  - Computes JD hash
  - Queries DB for all candidate scores for that JD
  - Displays ranked shortlist
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from core.config import settings
from core.database import init_db, get_scores_for_jd, compute_jd_hash
from agents.ranking_agent.scorer import SHORTLIST_CUTOFF


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch.py \"Job Description\"")
        sys.exit(1)

    jd = sys.argv[1]
    jd_hash = compute_jd_hash(jd)

    settings.validate_and_print()
    init_db()

    print(f"\n{'═'*60}")
    print(f"  BATCH RANKINGS FROM DB")
    print(f"  JD Hash: {jd_hash[:16]}...")
    print(f"{'═'*60}")

    scores = get_scores_for_jd(jd_hash)

    if not scores:
        print("\n  No candidates found for this job description.")
        return

    # Sort by composite score descending
    shortlisted = sorted(
        [s for s in scores if s["status"] == "shortlisted"],
        key=lambda x: x["composite_score"],
        reverse=True,
    )
    rejected = sorted(
        [s for s in scores if s["status"] == "rejected"],
        key=lambda x: x["composite_score"],
        reverse=True,
    )

    print(f"\n{'═'*60}")
    print(f"  FINAL SHORTLIST")
    print(f"  Total stored : {len(scores)}  |  "
          f"Shortlisted : {len(shortlisted)}  |  "
          f"Rejected : {len(rejected)}")
    print(f"  Cutoff score : {SHORTLIST_CUTOFF}/100")
    print(f"{'═'*60}")

    if shortlisted:
        print("\n  ✅  SHORTLISTED (ranked best → worst):\n")
        for rank, s in enumerate(shortlisted, 1):
            print(f"  #{rank}  {s['candidate_id']}  ({s['github']})")
            print(f"       Composite score : {s['composite_score']}/100  [{s['tier'].upper()}]")
            print(f"       Status          : {s['status']}")
            print(f"       Rationale       : {s['rationale']}")
            print(f"       Components      : {s['components']}")
            print(f"       Created at      : {s['created_at']}")
            print()
    else:
        print("\n  ⚠  No candidates met the shortlist cutoff score.\n")

    if rejected:
        print(f"  ❌  REJECTED (below cutoff {SHORTLIST_CUTOFF}/100):\n")
        for s in rejected:
            print(f"       {s['candidate_id']} ({s['github']}) "
                  f"— score {s['composite_score']}/100")

    # Save to JSON
    output_file = f"batch_rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    full_result = {
        "jd_hash": jd_hash,
        "jd": jd,
        "run_at": datetime.utcnow().isoformat(),
        "total_stored": len(scores),
        "shortlisted_count": len(shortlisted),
        "cutoff_score": SHORTLIST_CUTOFF,
        "shortlisted": shortlisted,
        "rejected": rejected,
    }
    with open(output_file, "w") as f:
        json.dump(full_result, f, indent=2, default=str)
    print(f"\n  Rankings saved → {output_file}")


if __name__ == "__main__":
    main()