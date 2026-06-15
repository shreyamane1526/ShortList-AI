from fastapi import APIRouter

from core.config import settings


router = APIRouter()


@router.get("/config")
async def config():

    return {
        "groq_model": settings.GROQ_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "match_threshold": settings.MATCH_THRESHOLD,
        "mock_mode": settings.use_mock,
        "github_auth": bool(
            settings.GITHUB_TOKEN
        ),
        "database": (
            "postgresql"
            if settings.is_postgres
            else "sqlite"
        ),
    }