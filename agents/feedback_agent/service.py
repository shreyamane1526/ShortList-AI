import time
from langsmith import traceable
from telemetry.logging.logger import (
    logger,
)

from agents.base_service import (
    BaseAgentService,
)

from agents.feedback_agent.agent import (
    feedback_agent_node,
)


class FeedbackAgentService(
    BaseAgentService
):
    @traceable(
        name="Feedback Agent"
    )

    def run(
        self,
        payload,
    ):

        start = time.time()

        logger.info(
            "Feedback Agent started"
        )

        try:

            result = (
                feedback_agent_node(
                    payload
                )
            )

            duration = round(
                time.time() - start,
                2,
            )

            logger.info(
                f"Feedback Agent completed "
                f"in {duration}s"
            )

            return result

        except Exception as e:

            logger.error(
                f"Feedback Agent failed: {e}"
            )

            raise