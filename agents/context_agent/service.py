import time
from langsmith import traceable
from telemetry.logging.logger import (
    logger,
)

from agents.base_service import (
    BaseAgentService,
)

from agents.context_agent.agent import (
    context_agent_node,
)


class ContextAgentService(
    BaseAgentService
):

    @traceable(
        name="Context Agent"
    )
    def run(
        self,
        payload,
    ):

        start = time.time()

        logger.info(
            "Context Agent started"
        )

        try:

            result = (
                context_agent_node(
                    payload
                )
            )

            duration = round(
                time.time() - start,
                2,
            )

            logger.info(
                f"Context Agent completed "
                f"in {duration}s"
            )

            return result

        except Exception as e:

            logger.error(
                f"Context Agent failed: {e}"
            )

            raise