from abc import ABC, abstractmethod


class BaseAgentService(ABC):

    @abstractmethod
    async def run(
        self,
        payload,
    ):
        pass