import os

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from oauth.consent import create_consent_page
from oauth.storage import AuthorizationStore


def create_oauth_app(store: AuthorizationStore) -> Starlette:
    app = Starlette(
        routes=[
            Route(
                "/oauth/consent",
                create_consent_page(store),
                methods=["GET"],
            ),
        ],
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["MCP_SESSION_SECRET"],
        session_cookie="relay_mcp_session",
        max_age=600,
        same_site="lax",
        https_only=True,
    )

    return app
