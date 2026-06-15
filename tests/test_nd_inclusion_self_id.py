import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.reasoning_agent.feature_engineer import extract_features
from agents.reasoning_agent.nd_inclusion_node import nd_inclusion_node


def _state(neurodivergent):
    return {
        "candidate_id": "candidate_1",
        "github_username": "octocat",
        "job_description": "Backend engineer with Python and FastAPI",
        "candidate_nd_self_id": {
            "neurodivergent": neurodivergent,
            "nd_type": "ADHD" if neurodivergent is True else None,
        },
        "evidence": {
            "candidate_id": "candidate_1",
            "github_username": "octocat",
            "sources_used": ["github"],
            "skills": [],
            "signals": {
                "commit_consistency": "high",
                "project_complexity": "high",
                "domain_breadth": ["backend"],
                "total_repos_analyzed": 5,
                "dead_repo_count": 0,
            },
            "integrity": {"trust_score": 80, "flags": []},
            "scores": {"github_score": 70, "average_score": 70},
        },
        "role_fit": {
            "job_title": "Backend Engineer",
            "job_description_raw": "Backend engineer with Python and FastAPI",
            "job_description_summary": "Backend engineer",
            "required_skills_matched": [
                {"skill_name": "Python", "required": True, "match_score": 1.0, "matched": True},
                {"skill_name": "FastAPI", "required": True, "match_score": 0.0, "matched": False},
            ],
            "preferred_skills_matched": [],
            "overall_fit_score": 0.5,
            "domains_required": ["backend"],
        },
        "errors": [],
    }


def test_self_declared_nd_takes_priority_and_adjusts_features():
    result = nd_inclusion_node(_state(True))["nd_inclusion"]

    assert result["nd_flag"] is True
    assert result["nd_source"] == "self_declared"
    assert result["nd_type"] == "adhd"
    assert result["penalty_reduction_weight"] >= 0.05

    before = extract_features(_state(True)["evidence"], _state(True)["role_fit"]).to_dict()
    after = extract_features(_state(True)["evidence"], _state(True)["role_fit"], result).to_dict()
    assert after["required_match_ratio"] > before["required_match_ratio"]


def test_false_self_id_uses_inference():
    result = nd_inclusion_node(_state(False))["nd_inclusion"]

    assert result["nd_flag"] is True
    assert result["nd_source"] == "inferred"


def test_null_self_id_falls_back_to_detection():
    result = nd_inclusion_node(_state(None))["nd_inclusion"]

    assert result["nd_flag"] is True
    assert result["nd_source"] == "inferred"
