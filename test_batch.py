"""
test_batch.py — Multi-candidate batch test for Shortlist AI

HOW TO USE:
1. Add your real candidates in the CANDIDATES list below
2. Edit the JOB_DESCRIPTION to match your actual role
3. Run:  python test_batch.py

What it does:
  - Runs each candidate through the full pipeline (Agent 1 → 2 → 3)
  - Collects all results
  - Passes them all to the Ranking Agent (Agent 4) together
  - Prints a final ordered shortlist comparing all candidates

Add as many or as few candidates as you want.
Even 1 candidate works — it just shows shortlisted/rejected with no ranking.
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime
from typing import List

from dotenv import load_dotenv
load_dotenv()

from core.config   import settings
from core.database import init_db, save_score, compute_jd_hash
from core.schemas  import PipelineRequest, AccessibilityMode
from pipeline      import run_pipeline
from agents.ranking_agent.scorer import compute_score, SHORTLIST_CUTOFF


# ═══════════════════════════════════════════════════════════════════════
# ✏️  INTERACTIVE MODE — Enter candidates in terminal
# ═══════════════════════════════════════════════════════════════════════

def get_candidates_interactive():
    """Prompt user to enter candidates interactively."""
    candidates = []
    print("\n" + "="*60)
    print("  ENTER CANDIDATES FOR BATCH TESTING")
    print("="*60)
    print("Enter candidate details. Press Enter for optional fields.")
    print("Type 'done' when finished.\n")

    while True:
        print(f"\nCandidate #{len(candidates) + 1}:")
        github = input("GitHub username (required): ").strip()
        if github.lower() == 'done':
            break
        if not github:
            print("GitHub username is required. Try again.")
            continue

        candidate_id = f"candidate_{len(candidates) + 1}"
        leetcode = input("LeetCode username (optional): ").strip() or None
        portfolio = input("Portfolio URL (optional): ").strip() or None
        resume = input("Resume PDF URL (optional): ").strip() or None
        mode = input("Accessibility mode (standard/adhd/dyslexia/autism) [standard]: ").strip().lower()
        if mode not in ['standard', 'adhd', 'dyslexia', 'autism']:
            mode = 'standard'

        candidates.append({
            "candidate_id": candidate_id,
            "github_username": github,
            "leetcode_username": leetcode,
            "portfolio_url": portfolio,
            "resume_url": resume,
            "accessibility_mode": mode,
        })

        print(f"✓ Added candidate: {github}")

    return candidates

# Uncomment to use interactive mode instead of hardcoded list
# CANDIDATES = get_candidates_interactive()

# Hardcoded for now - replace with interactive call above
# CANDIDATES = [
#     {
#         "candidate_id":      "candidate_1",
#         "github_username":   "octocat",
#         "leetcode_username": None,
#         "portfolio_url":     None,
#         "resume_url":        None,
#         "accessibility_mode": "standard",
#     },
# ]

JOB_DESCRIPTION = """
We are looking for a Backend Engineer with:
- Strong Python skills (required)
- FastAPI or Django experience (required)
- PostgreSQL or MySQL (required)
- Docker and Kubernetes (preferred)
- System design experience (preferred)
- REST API development (required)
Experience with CI/CD pipelines a plus. Remote-friendly team.
"""

JOB_ID    = "batch_test_001"     # any unique id for this hiring round
JOB_TITLE = "Backend Engineer"   # title of the role

# ═══════════════════════════════════════════════════════════════════════


def run_batch():
    # Get candidates interactively
    candidates = get_candidates_interactive()

    if not candidates:
        print("\nNo candidates entered. Exiting.")
        return

    settings.validate_and_print()
    init_db()

    print(f"\n{'═'*60}")
    print(f"  BATCH TEST — {JOB_TITLE}")
    print(f"  {len(candidates)} candidate(s) to evaluate")
    print(f"{'═'*60}")

    # ── Step 1: Run each candidate through full pipeline (Agents 1→2→3) ──
    results = []
    failed  = []

    for i, cand in enumerate(candidates, 1):
        print(f"\n[{i}/{len(candidates)}] Running pipeline for: {cand['github_username']}")
        print(f"{'─'*55}")

        try:
            request = PipelineRequest(
                candidate_id       = cand["candidate_id"],
                github_username    = cand["github_username"],
                job_description    = JOB_DESCRIPTION,
                leetcode_username  = cand.get("leetcode_username"),
                portfolio_url      = cand.get("portfolio_url"),
                resume_url         = cand.get("resume_url"),
                accessibility_mode = AccessibilityMode(
                    cand.get("accessibility_mode", "standard")
                ),
            )
            response = run_pipeline(request, include_ranking=False)  # Run only to Agent 3

            if response.errors:
                print(f"  ⚠  Warnings: {response.errors}")

            results.append({
                "candidate_id":    cand["candidate_id"],
                "github_username": cand["github_username"],
                "response":        response,
            })

            # Quick per-candidate summary
            print(f"  ✓  Agent 3 score  : {response.score}/100")
            print(f"  ✓  Recommendation : {response.recommendation}")
            print(f"  ✓  Trust score    : {response.trust_score}/100")
            fit = f"{response.overall_fit_score:.0%}" if response.overall_fit_score else "N/A"
            print(f"  ✓  Role fit       : {fit}")

        except Exception as exc:
            print(f"  ✗  FAILED: {exc}")
            failed.append(cand["candidate_id"])

    if not results:
        print("\n✗ No candidates completed the pipeline. Check your inputs.")
        return

    # ── Step 2: Build upstream dicts for Ranking Agent ───────────────────
    print(f"\n{'═'*60}")
    print(f"  RANKING {len(results)} candidate(s)...")
    print(f"{'═'*60}")

    ranked_candidates = []

    for item in results:
        resp = item["response"]

        # Rebuild the evidence/role_fit/insight dicts the ranking agent needs
        # These come from what run_pipeline already computed internally
        evidence = {
            "candidate_id":   item["candidate_id"],
            "github_username": item["github_username"],
            "integrity": {
                "trust_score": resp.trust_score or 50,
            },
            "nd_flags": [],
        }

        role_fit = {
            "overall_fit_score": resp.overall_fit_score or 0.0,
            "job_title":         JOB_TITLE,
        }

        insight = {
            "score":          resp.score or 0,
            "recommendation": resp.recommendation or "no",
            "strengths":      resp.strengths or [],
            "skill_gaps":     resp.skill_gaps or [],
            "nd_strengths":   resp.nd_strengths or [],
        }

        # Compute ranking score
        score_dict = compute_score(evidence, role_fit, insight)

        # Save to DB
        jd_hash = compute_jd_hash(JOB_DESCRIPTION)
        save_score(jd_hash, item["candidate_id"], item["github_username"], item.get("leetcode_username") or "", score_dict)

        ranked_candidates.append({
            "candidate_id":    item["candidate_id"],
            "github_username": item["github_username"],
            "composite_score": score_dict["composite_score"],
            "tier":            score_dict["tier"],
            "status":          score_dict["status"],
            "rationale":       score_dict["rationale"],
            "components":      score_dict["components"],
            "reasoning_score": resp.score or 0,
            "role_fit":        resp.overall_fit_score or 0.0,
            "trust_score":     resp.trust_score or 50,
            "recommendation":  resp.recommendation or "no",
            "strengths":       resp.strengths[:3] if resp.strengths else [],
            "skill_gaps":      resp.skill_gaps or [],
            "nd_strengths":    resp.nd_strengths or [],
        })

    # ── Step 3: Sort by composite score ───────────────────────────────────
    shortlisted = sorted(
        [c for c in ranked_candidates if c["status"] == "shortlisted"],
        key=lambda x: x["composite_score"],
        reverse=True,
    )
    rejected = sorted(
        [c for c in ranked_candidates if c["status"] == "rejected"],
        key=lambda x: x["composite_score"],
        reverse=True,
    )

    # ── Step 4: Print final shortlist ─────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  FINAL SHORTLIST — {JOB_TITLE}")
    print(f"  Evaluated : {len(results)}  |  "
          f"Shortlisted : {len(shortlisted)}  |  "
          f"Rejected : {len(rejected)}")
    print(f"  Cutoff score : {SHORTLIST_CUTOFF}/100")
    print(f"{'═'*60}")

    if shortlisted:
        print("\n  ✅  SHORTLISTED (ranked best → worst):\n")
        for rank, c in enumerate(shortlisted, 1):
            print(f"  #{rank}  {c['candidate_id']}  ({c['github_username']})")
            print(f"       Composite score : {c['composite_score']}/100  [{c['tier'].upper()}]")
            print(f"       Reasoning score : {c['reasoning_score']}/100")
            print(f"       Role fit        : {c['role_fit']:.0%}")
            print(f"       Trust score     : {c['trust_score']}/100")
            print(f"       Recommendation  : {c['recommendation']}")
            if c["nd_strengths"]:
                print(f"       ND strengths    : {len(c['nd_strengths'])} signal(s)")
            if c["strengths"]:
                print(f"       Top strengths   : {', '.join(c['strengths'][:3])}")
            if c["skill_gaps"]:
                gaps = [
                    g.get("skill_name","?")
                    for g in c["skill_gaps"]
                    if isinstance(g, dict) and g.get("severity") == "critical"
                ]
                if gaps:
                    print(f"       Critical gaps   : {', '.join(gaps)}")
            print(f"       Rationale       : {c['rationale']}")
            print()
    else:
        print("\n  ⚠  No candidates met the shortlist cutoff score.\n")

    if rejected:
        print(f"  ❌  REJECTED (below cutoff {SHORTLIST_CUTOFF}/100):\n")
        for c in rejected:
            print(f"       {c['candidate_id']} ({c['github_username']}) "
                  f"— score {c['composite_score']}/100 "
                  f"[{c['recommendation']}]")

    if failed:
        print(f"\n  ⚠  Failed to process: {failed}")

    # ── Step 5: Save full results to JSON ─────────────────────────────────
    output_file = f"batch_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    full_result = {
        "job_id":           JOB_ID,
        "job_title":        JOB_TITLE,
        "run_at":           datetime.utcnow().isoformat(),
        "total_evaluated":  len(results),
        "shortlisted_count":len(shortlisted),
        "cutoff_score":     SHORTLIST_CUTOFF,
        "shortlisted":      shortlisted,
        "rejected":         rejected,
        "failed":           failed,
    }
    with open(output_file, "w") as f:
        json.dump(full_result, f, indent=2, default=str)
    print(f"\n  Full results saved → {output_file}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    run_batch()