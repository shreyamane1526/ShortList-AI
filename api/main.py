"""
api/main.py

FastAPI application — HTTP layer over the pipeline.

Endpoints:
  GET  /health                    liveness check
  GET  /config                    current settings (no secrets)
  POST /evaluate                  run full pipeline for one candidate (Agents 1-5)
  GET  /api/feedback/{eval_id}    retrieve stored feedback report by evaluation_id
"""


from __future__ import annotations
import sys as _sys, os as _os
# Insert the project root (one level above api/) so all imports resolve correctly
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
del _sys, _os


from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


from core.config   import settings
from core.database import init_db
from core.schemas  import (
    PipelineRequest,
    PipelineResponse,
    RecruiterFeedbackRequest,
    RecruiterFeedbackResponse,
)
from pipeline      import run_pipeline
from repositories.recruiter_feedback_repository import (
    save_recruiter_feedback,
)
from api.routes.admin_routes import router as admin_router
app.include_router(admin_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_and_print()
    init_db()
    yield


app = FastAPI(
    title       = "Shortlist AI",
    description = "Bias-aware multi-agent hiring intelligence API",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "mock_mode": settings.use_mock,
        "database":  "postgresql" if settings.is_postgres else "sqlite",
    }


@app.get("/config")
async def config():
    return {
        "groq_model":      settings.GROQ_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "match_threshold": settings.MATCH_THRESHOLD,
        "mock_mode":       settings.use_mock,
        "github_auth":     bool(settings.GITHUB_TOKEN),
        "database":        "postgresql" if settings.is_postgres else "sqlite",
    }


@app.post("/evaluate", response_model=PipelineResponse)
async def evaluate(request: PipelineRequest):
    """
    Run the full Agent 1 → 2 → 3 → 4 → 5 pipeline.

    Example:
    {
      "candidate_id":    "priya_001",
      "github_username": "torvalds",
      "job_description": "Backend engineer with Python and FastAPI...",
      "accessibility_mode": "adhd"
    }

    The response includes:
      - feedback_report          : full Agent 5 JSON (inline)
      - feedback_evaluation_id   : key for GET /api/feedback/<id>
    """
    try:
        return run_pipeline(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/recruiter-feedback",
    response_model=RecruiterFeedbackResponse,
    status_code=201,
)
async def recruiter_feedback(
    request: RecruiterFeedbackRequest,
):
    """
    Capture recruiter decisions as ground-truth labels
    for continuous model learning.
    """
    try:
        row = save_recruiter_feedback(
            candidate_id=request.candidate_id,
            ai_prediction=request.ai_prediction,
            recruiter_decision=request.recruiter_decision,
            override_reason=request.override_reason,
            final_hiring_outcome=request.final_hiring_outcome,
            jd_hash=request.jd_hash,
            model_version=request.model_version,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return RecruiterFeedbackResponse(
        id=row.id,
        candidate_id=row.candidate_id,
        recruiter_decision=row.recruiter_decision,
        final_hiring_outcome=row.final_outcome,
        created_at=row.created_at,
    )


# ── Feedback report retrieval ─────────────────────────────────────────────────

@app.get("/api/feedback/{evaluation_id:path}")
async def get_feedback(evaluation_id: str):
    """
    Retrieve a stored feedback report by evaluation_id.

    evaluation_id format: <jd_hash>:<candidate_id>
    (returned as feedback_evaluation_id in the /evaluate response)

    Returns the full structured feedback JSON:
      {
        "why_not_selected":          { ... },
        "improvement_plan":          { ... },
        "learning_path":             [ ... ],
        "skill_match_visualization": { ... },
        "confidence_score":          { ... },
        "badges":                    [ ... ],
        "candidate_report_markdown": "...",
        "recruiter_summary":         "...",
        "_meta": { "evaluation_id", "generated_at", "generation_time_ms" }
      }
    """
    from core.database import get_feedback_report

    report = get_feedback_report(evaluation_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No feedback report found for evaluation_id '{evaluation_id}'. "
                   "Run /evaluate first to generate one.",
        )
    return report
