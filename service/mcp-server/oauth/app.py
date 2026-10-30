import os

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from oauth.approval import create_approval_handler
from oauth.codes import AuthorizationCodeStore
from oauth.consent import create_consent_page
from oauth.login import LoginStore, create_login_handler
from oauth.storage import AuthorizationStore


def create_oauth_app(store: AuthorizationStore) -> Starlette:
    # Temporary stores for the OAuth demonstration.
    login_store = LoginStore()
    code_store = AuthorizationCodeStore()

    app = Starlette(
        routes=[
            # Display OAuth authorization details.
            Route(
                "/oauth/consent",
                create_consent_page(store),
                methods=["GET"],
            ),

            # Authenticate through Relay's existing Auth Service.
            Route(
                "/oauth/login",
                create_login_handler(
                    store,
                    login_store,
                ),
                methods=["POST"],
            ),

            # Approve or deny OAuth access.
            Route(
                "/oauth/approve",
                create_approval_handler(
                    authorization_store=store,
                    login_store=login_store,
                    code_store=code_store,
                    public_origin=os.environ.get(
                        "MCP_PUBLIC_ORIGIN",
                        "https://mcp.relay.shaad.site",
                    ),
                ),
                methods=["POST"],
            ),
        ],
    )

    # Expose stores for local integration testing.
    app.state.authorization_store = store
    app.state.login_store = login_store
    app.state.code_store = code_store

    # Secure, signed browser sessions.
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["MCP_SESSION_SECRET"],
        session_cookie="relay_mcp_session",
        max_age=600,
        same_site="lax",
        https_only=True,
    )

    return app
