import os

from starlette.testclient import TestClient

from oauth.app import create_oauth_app
from oauth.storage import AuthorizationStore


assert os.environ.get("MCP_SESSION_SECRET")

app = create_oauth_app(AuthorizationStore())

with TestClient(app, base_url="https://testserver") as client:
    response = client.get("/oauth/consent")

    assert response.status_code == 400

    print("OAuth application: OK")
    print("Session middleware configured: OK")