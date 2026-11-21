import hmac
import logging

from redis.exceptions import RedisError

from app import rate_limit
from app.config import integer, required

LOGIN_FAILURES = integer("RATE_LIMIT_LOGIN_FAILURES", 10)
EMAIL_REQUESTS = integer("RATE_LIMIT_EMAIL_REQUESTS", 5)


def account_key(scope: str, email: str) -> str:
    digest = hmac.digest(
        required("JWT_SECRET_KEY").encode(),
        f"relay-rate-limit:{scope}:{email.strip().casefold()}".encode(),
        "sha256",
    ).hex()
    return f"auth:{scope}:{digest}"


async def limit_email(scope: str, email: str) -> None:
    await rate_limit.take(3600, (account_key(scope, email), EMAIL_REQUESTS))


# A slow successful login may finish after the next window has already begun.
_RELEASE = """
if redis.call('EXPIRETIME', KEYS[1]) == tonumber(ARGV[1]) then
    redis.call('DECR', KEYS[1])
end
"""


async def release(key: str, reset: int) -> None:
    """Refund an admitted successful login. An outage leaves a bounded reservation."""
    try:
        await rate_limit.client().eval(_RELEASE, 1, f"relay:ratelimit:{key}", reset)
    except RedisError:
        logging.getLogger(__name__).warning("Unable to release login rate limit reservation")
