
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp.server.auth.provider import AuthorizationParams

from oauth.consent import create_consent_page
from oauth.storage import AuthorizationStore


store = AuthorizationStore()

app = Starlette(
    routes=[
        Route(
            "/oauth/consent",
            create_consent_page(store),
        ),
    ],
)

params = AuthorizationParams(
    state="test-state",
    scopes=["workflows:read", "workflows:write"],
    code_challenge="test-challenge",
    redirect_uri="http://localhost:3000/callback",
    redirect_uri_provided_explicitly=True,
)

request_id = store.create("test-chat-client", params)

with TestClient(app) as client:
    response = client.get(
        "/oauth/consent",
        params={"request_id": request_id},
    )

    assert response.status_code == 200
    assert "test-chat-client" in response.text
    assert "workflows:read" in response.text

    print("Consent page: OK")
    print("Application displayed: OK")
    print("Permissions displayed: OK")