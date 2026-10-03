from abc import ABC, abstractmethod
from typing import Any


class Connector(ABC):

    @abstractmethod
    async def execute(
        self,
        action: str,
        config: dict[str, Any],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an action using this connector.
        """
        raise NotImplementedError