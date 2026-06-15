from fastapi import (
    APIRouter,
    HTTPException,
)

from core.schemas import (
    PipelineRequest,
    PipelineResponse,
)

from pipeline import run_pipeline


router = APIRouter()


@router.post(
    "/evaluate",
    response_model=PipelineResponse,
)
async def evaluate(
    request: PipelineRequest
):

    try:

        return run_pipeline(
            request
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )