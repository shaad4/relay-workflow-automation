import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grpc.integration_client import IntegrationGrpcClient
from app.services import workflow_service


@pytest.fixture
def integration_client(monkeypatch):
    """Keep lifecycle unit tests isolated from the Integration Service network."""
    client = AsyncMock(spec=IntegrationGrpcClient)
    monkeypatch.setattr(workflow_service, "IntegrationGrpcClient", lambda: client)
    return client
