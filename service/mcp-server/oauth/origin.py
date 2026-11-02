from urllib.parse import urlsplit

from starlette.requests import Request


def validate_browser_origin(
    request: Request,
    public_origin: str,
) -> bool:
    expected = public_origin.rstrip("/")
    origin = request.headers.get("origin")

    if origin is not None:
        return origin == expected

    referer = request.headers.get("referer")

    if not referer:
        return False

    try:
        parsed = urlsplit(referer)
    except ValueError:
        return False

    if not parsed.scheme or not parsed.netloc:
        return False

    referer_origin = f"{parsed.scheme}://{parsed.netloc}"

    return referer_origin == expected
