import os

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from oauth.consent import create_consent_page
from oauth.login import LoginStore, create_login_handler
from oauth.storage import AuthorizationStore


def create_oauth_app(store: AuthorizationStore) -> Starlette:
    login_store = LoginStore()

    app = Starlette(
        routes=[
            Route(
                "/oauth/consent",
                create_consent_page(store),
                methods=["GET"],
            ),
            Route(
                "/oauth/login",
                create_login_handler(store, login_store),
                methods=["POST"],
            ),
        ],
    )

    app.state.authorization_store = store
    app.state.login_store = login_store

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["MCP_SESSION_SECRET"],
        session_cookie="relay_mcp_session",
        max_age=600,
        same_site="lax",
        https_only=True,
    )

    return app
