"""
run.py  — CLI runner for Shortlist AI Pipeline

Usage:
  python run.py                                      # uses mock data + mock LLM
  python run.py --github torvalds --jd "..."         # real GitHub, mock LLM
  GROQ_API_KEY=gsk_xxx python run.py --github torvalds --jd "..."  # fully live
  python run.py --mode adhd                          # test inclusion middleware
  python run.py --github AdwikaVishal --nd-task      # generate ND-adapted task
"""

from __future__ import annotations

import os
import sys
import argparse
import json

# CRITICAL: Disable LangChain debug BEFORE any imports that might trigger it
os.environ["LANGCHAIN_DEBUG"] = "false"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.database import init_db
from core.schemas import PipelineRequest, AccessibilityMode
from pipeline import run_pipeline


# Default job description (moved BEFORE main() so it's defined when used)
DEFAULT_JD = """
We are looking for a Backend Engineer with:
- Strong Python skills (required)
- FastAPI or Django experience (required)
- PostgreSQL or MySQL (required)
- Docker and Kubernetes (preferred)
- System design experience (preferred)
- REST API development (required)
Experience with CI/CD pipelines a plus. Remote-friendly team.
"""


def main():
    parser = argparse.ArgumentParser(description="Shortlist AI — CLI runner")
    parser.add_argument("--github", default="octocat", help="GitHub username")
    parser.add_argument("--leetcode", default=None, help="LeetCode username (optional)")
    parser.add_argument("--portfolio", default=None, help="Portfolio URL (optional)")
    parser.add_argument("--resume", default=None, help="Resume URL (optional)")
    parser.add_argument("--jd", default=DEFAULT_JD, help="Job description text")
    parser.add_argument("--mode", default="standard",
                        choices=["standard", "adhd", "dyslexia", "autism"],
                        help="Accessibility mode")
    parser.add_argument("--output", default=None, help="Save full result to JSON file")
    parser.add_argument("--nd-task", action="store_true",
                        help="Generate ND-adapted work sample task for this candidate")
    parser.add_argument("--mock", action="store_true", default=False,
                        help="Force mock mode (overrides settings)")

    args = parser.parse_args()

    # Override mock setting if specified
    if args.mock:
        settings.use_mock = True

    # Validate and print config
    settings.validate_and_print()

    # Initialize database
    init_db()

    # Create pipeline request
    request = PipelineRequest(
        candidate_id=args.github,
        github_username=args.github,
        job_description=args.jd,
        leetcode_username=args.leetcode,
        portfolio_url=args.portfolio,
        resume_url=args.resume,
        accessibility_mode=AccessibilityMode(args.mode),
    )

    # Run pipeline
    response = run_pipeline(request)

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("  PIPELINE RESULT")
    print("═" * 55)
    print(f"  Candidate   : {response.candidate_id}")
    print(f"  Score       : {response.score}/100" if response.score else "  Score       : N/A")
    print(f"  Decision    : {str(response.recommendation).upper()}" if response.recommendation else "  Decision    : N/A")
    print(f"  Trust score : {response.trust_score}/100" if response.trust_score else "  Trust score : N/A")
    if response.overall_fit_score:
        print(f"  Fit score   : {response.overall_fit_score:.0%}")
    else:
        print("  Fit score   : N/A")
    print(f"  Duration    : {response.pipeline_duration_seconds}s")

    if response.recommendation_narrative:
        print(f"\n  Narrative:\n  {response.recommendation_narrative}")

    if response.strengths:
        print(f"\n  Strengths ({len(response.strengths)}):")
        for s in response.strengths:
            print(f"    • {s}")

    if response.skill_gaps:
        print(f"\n  Skill gaps ({len(response.skill_gaps)}):")
        for g in response.skill_gaps:
            if isinstance(g, dict):
                name = g.get("skill_name", "")
                sev = g.get("severity", "")
                print(f"    • [{sev.upper()}] {name}")
            else:
                print(f"    • {g}")

    if response.nd_strengths:
        print(f"\n  ND strengths ({len(response.nd_strengths)}):")
        for n in response.nd_strengths:
            if isinstance(n, dict):
                sig = n.get("signal", "")
                wt = n.get("weight", "")
                print(f"    • [{wt}] {sig}")
            else:
                print(f"    • {n}")

    if response.accessible_summary:
        print(f"\n  Accessible summary:\n{response.accessible_summary}")

    if response.errors:
        print(f"\n  ⚠ Errors: {response.errors}")

    if response.bias_audit:
        audit = response.bias_audit
        if isinstance(audit, dict):
            print(f"\n  Bias audit:")
            print(f"    ND detected    : {audit.get('nd_signal_detected')}")
            print(f"    Fairness score : {audit.get('fairness_score')}")
            print(f"    Proxies removed: {len(audit.get('proxies_removed', []))}")

    # ── ND Inclusion report ───────────────────────────────────────────────────
    if response.nd_inclusion:
        nd = response.nd_inclusion
        print(f"\n  ND Inclusion Report:")
        print(f"    ND flag          : {nd.get('nd_flag')}")
        print(f"    ND type          : {nd.get('nd_type')}")
        print(f"    Underest. risk   : {nd.get('risk_of_underestimation')}")
        print(f"    Action           : {nd.get('recommended_action')}")
        print(f"    Penalty reduction: {nd.get('penalty_reduction_weight', 0):.0%}")

        strengths = nd.get("strengths_detected", [])
        if strengths:
            print(f"    Strengths ({len(strengths)}):")
            for s in strengths:
                print(f"      [{s.get('weight', '')}] {s.get('strength_label', '')}")

        risks = nd.get("underestimation_risks", [])
        if risks:
            print(f"    Underestimation risks:")
            for r in risks:
                print(f"      [{r.get('severity', '')}] {r.get('risk_factor', '')}: {r.get('affected_metric', '')}")

    # ── ND-adapted task generation ────────────────────────────────────────────
    if args.nd_task and response.nd_inclusion:
        try:
            from agents.reasoning_agent.nd_task_generator import generate_task
            nd = response.nd_inclusion
            ev_dict = {}
            rf_dict = {
                "job_title": args.jd.split("\n")[0][:40] if args.jd else "Software Engineer",
                "domains_required": []
            }
            fmt = nd.get("task_format", "standard")
            task = generate_task(ev_dict, rf_dict, nd_format=fmt)

            print(f"\n  ND-Adapted Work Sample Task [{fmt.upper()} format]:")
            print(f"  Title    : {task.title}")
            print(f"  Duration : {task.duration_minutes} minutes")
            print(f"  Level    : {task.level}")
            print(f"  TTS      : {task.tts_enabled}")
            print(f"\n  --- PROBLEM STATEMENT ---")
            print(task.problem_statement)
            if hasattr(task, 'steps') and task.steps:
                print(f"\n  --- STEPS ---")
                for step in task.steps:
                    print(f"  Step {step.step_number} ({step.estimated_minutes}min): {step.instruction}")
        except ImportError:
            print("\n  ⚠ ND task generator not available – skipping")

    # ── Save to file ──────────────────────────────────────────────────────────
    if args.output:
        with open(args.output, "w") as f:
            json.dump(response.model_dump(mode="json"), f, indent=2, default=str)
        print(f"\n  Full result saved to: {args.output}")


if __name__ == "__main__":
    main()