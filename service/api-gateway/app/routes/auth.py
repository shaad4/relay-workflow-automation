from fastapi import APIRouter, Depends, Request
import httpx

from app.dependencies import get_current_identity
from app.core.proxy import build_proxy_response, AUTH_SERVICE_URL

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