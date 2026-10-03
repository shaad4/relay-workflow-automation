from app.connectors.base import Connector
from app.connectors.http import HTTPConnector
from app.connectors.gmail import GmailConnector
from app.connectors.mock_payment import MockPaymentConnector


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


connector_registry = ConnectorRegistry()

connector_registry.register("http", HTTPConnector())
connector_registry.register("gmail", GmailConnector())
connector_registry.register("mock_payment", MockPaymentConnector())