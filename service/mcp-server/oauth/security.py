import secrets

from starlette.requests import Request


def validate_csrf(request: Request, submitted_token: str) -> bool:
    expected_token = request.session.get("csrf_token")

    if not expected_token or not submitted_token:
        return False

    return secrets.compare_digest(
        expected_token,
        submitted_token,
    )
