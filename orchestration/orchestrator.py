from agents.context_agent import (
    extractor,
)


class HiringOrchestrator:

    async def run_context_stage(
        self,
        job_description: str,
    ):

        result = (
            extractor.extract_context(
                job_description
            )
        )

        return result