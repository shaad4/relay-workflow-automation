import secrets
import time
from dataclasses import dataclass

from mcp.server.auth.provider import AuthorizationParams


@dataclass
class PendingAuthorization:
    client_id: str
    params: AuthorizationParams
    expires_at: float


class AuthorizationStore:
    def __init__(self):
        self.requests: dict[str, PendingAuthorization] = {}

    def create(
        self,
        client_id: str,
        params: AuthorizationParams,
    ) -> str:
        self.cleanup()
        now = time.time()

        request_id = secrets.token_urlsafe(32)

        self.requests[request_id] = PendingAuthorization(
            client_id=client_id,
            params=params,
            expires_at=now + 300,
        )

        return request_id

    def cleanup(self):
        now = time.time()
        self.requests = {k: v for k, v in self.requests.items() if v.expires_at > now}

    def consume(self, request_id: str) -> PendingAuthorization | None:
        # Each authorization request can only be consumed once.
        request = self.requests.pop(request_id, None)

        if request is None or request.expires_at <= time.time():
            return None

        return request

    def get(self, request_id: str) -> PendingAuthorization | None:
        request = self.requests.get(request_id)

        if request is None:
            return None

        if request.expires_at <= time.time():
            self.requests.pop(request_id, None)
            return None

        return request
