import time
from langsmith import traceable
from telemetry.logging.logger import (
    logger,
)

from agents.base_service import (
    BaseAgentService,
)

from agents.evidence_agent.agent import (
    evidence_agent_node,
)


class EvidenceAgentService(
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
            "Evidence Agent started"
        )

        try:

            result = (
                evidence_agent_node(
                    payload
                )
            )

            duration = round(
                time.time() - start,
                2,
            )

            logger.info(
                f"Evidence Agent completed "
                f"in {duration}s"
            )

            return result

        except Exception as e:

            logger.error(
                f"Evidence Agent failed: {e}"
            )

            raise