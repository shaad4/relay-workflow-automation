
from unittest.mock import Mock

from oauth.security import validate_csrf


request = Mock()
request.session = {
    "csrf_token": "test-secret-token",
}

assert validate_csrf(request, "test-secret-token")
assert not validate_csrf(request, "wrong-token")
assert not validate_csrf(request, "")

request.session = {}
assert not validate_csrf(request, "test-secret-token")

print("Valid CSRF token: OK")
print("Invalid CSRF token rejected: OK")
print("Missing CSRF token rejected: OK")
