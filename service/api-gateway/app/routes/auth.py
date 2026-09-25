import httpx
from fastapi import APIRouter, Depends, Request

from app.core.proxy import AUTH_SERVICE_URL, build_proxy_response
from app.dependencies import get_current_identity

router = APIRouter(prefix="/auth")


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