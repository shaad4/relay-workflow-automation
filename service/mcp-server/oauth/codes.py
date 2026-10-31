import secrets
import time

from mcp.server.auth.provider import AuthorizationCode
from pydantic import ConfigDict
from user_session import UserRelaySession


class DelegatedCode(AuthorizationCode):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    relay_session: UserRelaySession


class AuthorizationCodeStore:
    def __init__(self):
        self.codes = {}

    def cleanup(self):
        now = time.time()
        self.codes = {k: v for k, v in self.codes.items() if v.expires_at > now}

    def create(self, client_id, params, user_id, relay_session):
        self.cleanup()
        code = secrets.token_urlsafe(32)
        self.codes[code] = DelegatedCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + 60,
            client_id=client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
            subject=user_id,
            relay_session=relay_session,
        )
        return code

    def get(self, code, client_id):
        self.cleanup()
        authorization = self.codes.get(code)
        if authorization and authorization.client_id == client_id:
            return authorization
        return None

    def consume(self, code, client_id):
        authorization = self.get(code, client_id)
        if authorization:
            self.codes.pop(code)
        return authorization
