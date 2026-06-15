import time
from langsmith import traceable
from telemetry.logging.logger import (
    logger,
)

from agents.base_service import (
    BaseAgentService,
)

from agents.ranking_agent.agent import (
    ranking_agent_node,
)


class RankingAgentService(
    BaseAgentService
):
    @traceable(
        name="Ranking Agent"
    )

    def run(
        self,
        payload,
    ):

        start = time.time()

        logger.info(
            "Ranking Agent started"
        )

        try:

            result = (
                ranking_agent_node(
                    payload
                )
            )

            duration = round(
                time.time() - start,
                2,
            )

            logger.info(
                f"Ranking Agent completed "
                f"in {duration}s"
            )

            return result

        except Exception as e:

            logger.error(
                f"Ranking Agent failed: {e}"
            )

            raise