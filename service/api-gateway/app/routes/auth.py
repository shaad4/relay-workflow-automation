import httpx
from fastapi import APIRouter, Depends, Request

from app.core.proxy import AUTH_SERVICE_URL, build_proxy_response, proxy_request
from app.dependencies import get_current_identity

router = APIRouter(prefix="/auth")


@router.post("/logout")
async def logout(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/logout")


@router.get("/me")
async def current_user(
    request: Request,
    identity: dict = Depends(get_current_identity),
):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/auth/me",
            headers={
                "Authorization": request.headers.get("Authorization", ""),
            },
        )

    return build_proxy_response(response)
