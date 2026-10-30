import secrets
import time

from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
)


class AuthorizationCodeStore:
    def __init__(self):
        self.codes: dict[str, AuthorizationCode] = {}

    def create(
        self,
        client_id: str,
        params: AuthorizationParams,
        user_id: str,
    ) -> str:
        code = secrets.token_urlsafe(32)

        self.codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + 60,
            client_id=client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=(
                params.redirect_uri_provided_explicitly
            ),
            resource=params.resource,
            subject=user_id,
        )

        return code

    def consume(
        self,
        code: str,
        client_id: str,
    ) -> AuthorizationCode | None:
        authorization = self.codes.pop(code, None)

        if authorization is None:
            return None

        if authorization.expires_at <= time.time():
            return None

        if authorization.client_id != client_id:
            return None

        return authorization
