from fastapi import APIRouter

from core.config import settings


router = APIRouter()


@router.get("/health")
async def health():

    return {
        "status": "ok",
        "mock_mode": settings.use_mock,
        "database": (
            "postgresql"
            if settings.is_postgres
            else "sqlite"
        ),
    }