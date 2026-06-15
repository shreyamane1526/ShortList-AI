from fastapi import APIRouter

from core.schemas import (
    PipelineRequest,
)

from pipeline import run_pipeline


router = APIRouter()


@router.post("/run")


async def run_context_pipeline(
    request: PipelineRequest
):

    result = run_pipeline(
        request
    )

    return result