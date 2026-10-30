"""SDK-compatible revocation with an optional secret for public/Basic clients."""

from mcp.server.auth.handlers.revoke import RevocationRequest
from mcp.server.auth.middleware.client_auth import AuthenticationError, ClientAuthenticator
from pydantic import ValidationError
from starlette.responses import JSONResponse, Response


def create_revocation_handler(provider):
    async def revoke(request):
        form = await request.form()
        if len(form.multi_items()) != len(form):
            return JSONResponse({"error": "invalid_request"}, status_code=400)
        try:
            client = await ClientAuthenticator(provider).authenticate_request(request)
        except AuthenticationError:
            return JSONResponse({"error": "invalid_client"}, status_code=401)
        try:
            # SDK 2.3.0's nullable field has no default, incorrectly making it required.
            params = RevocationRequest.model_validate({"client_secret": None, **dict(form)})
        except ValidationError:
            return JSONResponse({"error": "invalid_request"}, status_code=400)
        token = await provider.load_access_token(params.token)
        if token is None:
            token = await provider.load_refresh_token(client, params.token)
        if token and token.client_id == client.client_id:
            await provider.revoke_token(token)
        return Response(status_code=200)

    return revoke
