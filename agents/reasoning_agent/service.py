import time
from langsmith import traceable
from telemetry.logging.logger import (
    logger,
)

from agents.base_service import (
    BaseAgentService,
)

from agents.reasoning_agent.agent import (
    reasoning_agent_node,
)


class ReasoningAgentService(
    BaseAgentService
):
    @traceable(
        name="Evidence Agent"
    )

    def run(
        self,
        payload,
    ):

        start = time.time()

        logger.info(
            "Reasoning Agent started"
        )

        try:

            result = (
                reasoning_agent_node(
                    payload
                )
            )

            duration = round(
                time.time() - start,
                2,
            )

            logger.info(
                f"Reasoning Agent completed "
                f"in {duration}s"
            )

            return result

        except Exception as e:

            logger.error(
                f"Reasoning Agent failed: {e}"
            )

            raise