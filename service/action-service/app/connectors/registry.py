from app.connectors.base import Connector


class ConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, Connector] = {}

    def register(self, provider: str, connector: Connector) -> None:
        self._connectors[provider] = connector

    def get(self, provider: str) -> Connector:
        connector = self._connectors.get(provider)

        if connector is None:
            raise ValueError(f"Connector not found: {provider}")

        return connector