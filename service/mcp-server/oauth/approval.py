from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from oauth.codes import AuthorizationCodeStore
from oauth.login import LoginStore
from oauth.security import validate_csrf
from oauth.storage import AuthorizationStore


def create_approval_handler(
    authorization_store: AuthorizationStore,
    login_store: LoginStore,
    code_store: AuthorizationCodeStore,
    public_origin: str,
):
    async def approve(request: Request):
        expected_origin = public_origin.rstrip("/")

        if request.headers.get("origin") != expected_origin:
            return HTMLResponse("Invalid origin", status_code=403)

        form = await request.form()

        request_id = str(form.get("request_id", ""))
        csrf_token = str(form.get("csrf_token", ""))
        decision = str(form.get("decision", ""))

        if request.session.get("oauth_request_id") != request_id or not validate_csrf(
            request, csrf_token
        ):
            return HTMLResponse(
                "Invalid authorization session",
                status_code=403,
            )

        pending = authorization_store.get(request_id)

        if pending is None:
            return HTMLResponse(
                "Authorization request expired",
                status_code=400,
            )

        login_id = request.session.get("relay_login_session")

        login_session = login_store.get(login_id) if login_id else None

        if login_session is None:
            return HTMLResponse(
                "Relay login required",
                status_code=401,
            )

        if decision not in {"approve", "deny"}:
            return HTMLResponse(
                "Invalid decision",
                status_code=400,
            )

        # Consume the authorization request only
        # after verifying the browser and login session.
        pending = authorization_store.consume(request_id)

        if pending is None:
            return HTMLResponse(
                "Authorization request already used",
                status_code=400,
            )

        redirect_uri = str(pending.params.redirect_uri)
        parsed = urlsplit(redirect_uri)
        query = dict(parse_qsl(parsed.query))

        if decision == "deny":
            query.update(
                {
                    "error": "access_denied",
                    "state": pending.params.state or "",
                }
            )
        else:
            user_id = login_session["identity"]["user_id"]

            code = code_store.create(
                client_id=pending.client_id,
                params=pending.params,
                user_id=user_id,
                relay_session=login_session["relay_session"],
            )

            query.update(
                {
                    "code": code,
                    "state": pending.params.state or "",
                }
            )

        callback_url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query),
                parsed.fragment,
            )
        )

        login_store.sessions.pop(login_id, None)
        request.session.pop("oauth_request_id", None)
        request.session.pop("csrf_token", None)
        request.session.pop("relay_login_session", None)

        return RedirectResponse(
            callback_url,
            status_code=303,
        )

    return approve
