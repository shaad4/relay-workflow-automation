
from starlette.testclient import TestClient

from mcp.server.auth.provider import AuthorizationParams

from oauth.app import create_oauth_app
from oauth.storage import AuthorizationStore


store = AuthorizationStore()
app = create_oauth_app(store)


def create_request():
    params = AuthorizationParams(
        state="test-state",
        scopes=["workflows:read"],
        code_challenge="test-challenge",
        redirect_uri="http://localhost:3000/callback",
        redirect_uri_provided_explicitly=True,
    )

    return store.create("test-client", params)


first_id = create_request()
second_id = create_request()


with TestClient(app, base_url="https://testserver") as client:
    # First authorization request
    first = client.get(
        "/oauth/consent",
        params={"request_id": first_id},
    )

    assert first.status_code == 200

    # Different authorization request in same browser
    second = client.get(
        "/oauth/consent",
        params={"request_id": second_id},
    )

    assert second.status_code == 400

    # Original request should still work
    original = client.get(
        "/oauth/consent",
        params={"request_id": first_id},
    )

    assert original.status_code == 200

    print("Browser session binding: OK")
    print("Different authorization request rejected: OK")
    print("Original authorization request preserved: OK")
