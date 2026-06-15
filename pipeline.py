from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional, TypedDict
from langsmith import traceable
# from LinkedInHackathon.agents.context_agent.service import ContextAgentService

# Disable LangChain debug (avoids AttributeError: module 'langchain' has no attribute 'debug')
os.environ["LANGCHAIN_DEBUG"] = "false"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


print(
    "LANGCHAIN_TRACING_V2 =",
    os.getenv("LANGCHAIN_TRACING_V2")
)

print(
    "LANGCHAIN_PROJECT =",
    os.getenv("LANGCHAIN_PROJECT")
)
# from asyncio import graph
from langgraph.graph import StateGraph, END

from agents.context_agent.service import (
    ContextAgentService,
)

from agents.evidence_agent.service import (
    EvidenceAgentService,
)

from agents.reasoning_agent.service import (
    ReasoningAgentService,
)

from agents.ranking_agent.service import (
    RankingAgentService,
)

from agents.feedback_agent.service import (
    FeedbackAgentService,
)
from agents.reasoning_agent.nd_inclusion_node import nd_inclusion_node

from core.config import settings
from core.schemas import (
    AccessibilityMode, HiringState,
    PipelineRequest, PipelineResponse,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Wrap nodes with error handling
# ═══════════════════════════════════════════════════════════════════════════════

def wrap_node(node_func, node_name: str):

    def wrapped(state: dict) -> dict:

        print(f"[{node_name}] Running...")

        try:

            return node_func(state)

        except Exception as e:

            print(
                f"[{node_name}] ERROR: {str(e)}"
            )

            return {
                "errors": (
                    state.get("errors", [])
                    + [f"{node_name}: {str(e)}"]
                )
            }

    return wrapped

# ═══════════════════════════════════════════════════════════════════════════════
# LangGraph TypedDict — required by StateGraph (not Pydantic)
# ═══════════════════════════════════════════════════════════════════════════════

class GraphState(TypedDict, total=False):
    # inputs
    candidate_id:          str
    github_username:       str
    leetcode_username:     Optional[str]
    portfolio_url:         Optional[str]
    resume_url:            Optional[str]
    job_description:       str
    accessibility_profile: dict
    candidate_nd_self_id:  Optional[dict]
    inclusion_enabled:     bool
    use_mock:              bool                     # ← ADDED

    # agent outputs
    evidence:              Optional[dict]
    role_fit:              Optional[dict]
    nd_inclusion:          Optional[dict]
    insight:               Optional[dict]
    ranking_score:         Optional[float]
    ranking_justification: Optional[str]
    feedback_report:       Optional[dict]

    # bookkeeping
    errors:                List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Stub agents (Agents 4 + 5) — replace with real implementations
# ═══════════════════════════════════════════════════════════════════════════════

def ranking_agent_stub(state: dict) -> dict:
    """
    Agent 4 — Ranking Agent (stub).
    When implemented, it will:
      - Batch multiple candidates' HiringInsight objects
      - Compute weighted ranking: score × evidence_strength × role_fit
      - Run candidate↔JD cosine similarity using ChromaDB embeddings
      - Output ShortlistResult with top-N candidates and justifications
    See: core/schemas.py :: CandidateRank, ShortlistResult

    NOTE: LangGraph requires at least one field to be written per node.
    Stubs write 'errors' (unchanged) to satisfy this requirement.
    """
    print("[Agent 4 — Ranking] Stub — not yet implemented")
    return {"errors": state.get("errors", [])}


def feedback_agent_stub(state: dict) -> dict:
    """
    Agent 5 — Feedback Agent (stub).
    When implemented, it will:
      - Produce per-candidate skill gap + learning path reports
      - Apply ADHD/dyslexia formatting via the Inclusion middleware
      - Source free learning resources (freeCodeCamp, The Odin Project, fast.ai)

    NOTE: LangGraph requires at least one field to be written per node.
    """
    print("[Agent 5 — Feedback] Stub — not yet implemented")
    return {"errors": state.get("errors", [])}


# ═══════════════════════════════════════════════════════════════════════════════
# Graph construction
# ═══════════════════════════════════════════════════════════════════════════════

def build_pipeline(inclusion_enabled: bool = True) -> Any:
    """
    Compiles the LangGraph StateGraph.

    Graph edges:
      evidence → context → reasoning → ranking → feedback → END

    Inclusion middleware wraps:
      - reasoning node (pre: proxy masking + ND detection, post: accessible summary)
      - feedback node  (post: ADHD/dyslexia formatting)
    """
    graph = StateGraph(GraphState)

    # Node names must NOT match state keys (evidence, role_fit, insight, etc.)
    evidence_service = (
        EvidenceAgentService()
    )

    graph.add_node(
        "evidence_node",
        evidence_service.run,
    )
    

    context_service = (
        ContextAgentService()
    )

    graph.add_node(
        "context_node",
        context_service.run,
    )
    if inclusion_enabled:
        graph.add_node("nd_inclusion_node", nd_inclusion_node)
    reasoning_service = (
        ReasoningAgentService()
    )

    graph.add_node(
        "reasoning_node",
        wrap_node(
            reasoning_service.run,
            "reasoning",
        ),
    )
    ranking_service = (
        RankingAgentService()
    )

    graph.add_node(
        "ranking_node",
        wrap_node(
            ranking_service.run,
            "ranking",
        ),
    )
    feedback_service = (
        FeedbackAgentService()
    )

    graph.add_node(
        "feedback_node",
        wrap_node(
            feedback_service.run,
            "feedback",
        ),
    )

    graph.set_entry_point("evidence_node")
    graph.add_edge("evidence_node",     "context_node")
    if inclusion_enabled:
        graph.add_edge("context_node",      "nd_inclusion_node")
        graph.add_edge("nd_inclusion_node", "reasoning_node")
    else:
        graph.add_edge("context_node",      "reasoning_node")
    graph.add_edge("reasoning_node",    "ranking_node")
    graph.add_edge("ranking_node",      "feedback_node")
    graph.add_edge("feedback_node",     END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════════════════════
# Public run function — called by API and CLI
# ═══════════════════════════════════════════════════════════════════════════════

@traceable(
    name="Hiring Pipeline"
)
def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """
    Runs the full pipeline for one candidate + one job description.
    Returns a PipelineResponse ready for the API or CLI output.
    """
    pipeline = build_pipeline(inclusion_enabled=request.inclusion_enabled)
    started  = time.time()

    print(f"\n{'═'*55}")
    print(f"  Shortlist AI Pipeline")
    print(f"  Candidate : {request.candidate_id}  ({request.github_username})")
    print(f"  Mode      : {request.accessibility_mode}")
    print(f"  Mock      : {settings.use_mock}")
    print(f"{'═'*55}")

    initial: GraphState = {
        "candidate_id":    request.candidate_id,
        "github_username": request.github_username,
        "job_description": request.job_description,
        "use_mock":        settings.use_mock,           # ← ADDED
        "inclusion_enabled": request.inclusion_enabled,
        "accessibility_profile": {
            "mode":                request.accessibility_mode,
            "tts_enabled":         request.accessibility_mode == AccessibilityMode.DYSLEXIA,
            "step_by_step":        request.accessibility_mode == AccessibilityMode.ADHD,
            "simplified_language": request.accessibility_mode in (
                AccessibilityMode.ADHD, AccessibilityMode.DYSLEXIA
            ),
        },
        "errors": [],
    }

    # add optional fields only if present (avoids None keys confusing LangGraph)
    if request.leetcode_username:
        initial["leetcode_username"] = request.leetcode_username
    if request.portfolio_url:
        initial["portfolio_url"] = request.portfolio_url
    if request.resume_url:
        initial["resume_url"] = request.resume_url
    if request.candidate_nd_self_id:
        initial["candidate_nd_self_id"] = request.candidate_nd_self_id.model_dump()

    final    = pipeline.invoke(initial)
    duration = round(time.time() - started, 2)

    print(f"\n{'─'*55}")
    print(f"  Pipeline completed in {duration}s")
    print(f"  Errors: {final.get('errors', [])}")
    print(f"{'─'*55}\n")

    return _build_response(request.candidate_id, final, duration)


def _build_response(candidate_id: str, final: dict, duration: float) -> PipelineResponse:
    insight      = final.get("insight")       or {}
    evidence     = final.get("evidence")      or {}
    role_fit     = final.get("role_fit")      or {}
    nd_inclusion = final.get("nd_inclusion")  or {}
    integrity    = evidence.get("integrity")  or {}
    feedback = final.get("feedback_report") or {}
    return PipelineResponse(
        candidate_id             = candidate_id,
        score                    = insight.get("score"),
        recommendation           = insight.get("recommendation"),
        recommendation_narrative = insight.get("recommendation_narrative"),
        strengths                = insight.get("strengths", []),
        skill_gaps               = insight.get("skill_gaps", []),
        nd_strengths             = insight.get("nd_strengths", []),
        confidence_per_skill     = insight.get("confidence_per_skill", {}),
        overall_fit_score        = role_fit.get("overall_fit_score"),
        trust_score              = (integrity.get("trust_score")
                                    if isinstance(integrity, dict) else None),
        bias_audit               = insight.get("bias_audit"),
        reasoning_steps          = insight.get("reasoning_steps", []),
        accessible_summary       = insight.get("accessible_summary"),
        nd_inclusion             = nd_inclusion if nd_inclusion else None,
                why_not_selected = feedback.get(
            "why_not_selected"
        ),

        improvement_plan = feedback.get(
            "improvement_plan"
        ),

        learning_path = feedback.get(
            "learning_path",
            [],
        ),

        learning_roadmap = feedback.get(
            "learning_roadmap"
        ),

        skill_match_visualization = feedback.get(
            "skill_match_visualization"
        ),

        confidence_score = feedback.get(
            "confidence_score"
        ),

        badges = feedback.get(
            "badges",
            [],
        ),

        candidate_report_markdown = feedback.get(
            "candidate_report_markdown"
        ),

        recruiter_summary = feedback.get(
            "recruiter_summary"
        ),
        errors                   = final.get("errors", []),
        pipeline_duration_seconds = duration,
    )
