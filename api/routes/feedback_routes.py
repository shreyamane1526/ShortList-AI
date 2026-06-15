from fastapi import (
    APIRouter,
    HTTPException,
)

from core.database import (
    get_feedback_report,
)


router = APIRouter()


@router.get(
    "/feedback/{evaluation_id:path}"
)
async def get_feedback(
    evaluation_id: str,
):

    report = get_feedback_report(
        evaluation_id
    )

    if report is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Feedback report "
                "not found."
            ),
        )

    return report