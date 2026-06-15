from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Plugin interface. Add a new platform by subclassing this."""
    platform_name: str = "base"

    @abstractmethod
    async def collect(self, identifier: str) -> dict:
        """Always returns a dict — never raises. Include 'error' key on failure."""
        ...