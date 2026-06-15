from fastapi import FastAPI
from . import enrich_candidate_async, evaluate_candidate_for_job_async
from app import app as flask_app  # Need flask app context for DB

app = FastAPI(title="Agents API", version="1.0")

@app.get("/health")
def health():
    return {"status": "ok", "agents": ["evidence", "context", "reasoning", "ranking", "feedback"]}

@app.post("/enrich/{candidate_id}")
async def enrich_candidate(candidate_id: int, github: str = "", leetcode: str = "", resume: str = ""):
    enrich_candidate_async(flask_app, candidate_id, github, leetcode, resume)
    return {"status": "enrichment started async"}

@app.post("/evaluate/{evaluation_id}")
async def evaluate_job(evaluation_id: int):
    evaluate_candidate_for_job_async(flask_app, evaluation_id)
    return {"status": "evaluation started async"}

@app.get("/agents")
def agents():
    return {
        "agents": [
            {"id": "evidence", "status": "active"},
            {"id": "context", "status": "active"},
            {"id": "reasoning", "status": "active"},
            {"id": "ranking", "status": "active"},
            {"id": "feedback", "status": "active"},
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
