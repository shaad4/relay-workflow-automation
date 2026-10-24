from fastapi import APIRouter, Request

from app.core.proxy import AUTH_SERVICE_URL, proxy_request

router = APIRouter(prefix="/auth")


@router.api_route(
    "/login",
    methods=["POST"],
)
async def login(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/login")


@router.api_route(
    "/register",
    methods=["POST"],
)
async def register(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/register")


@router.api_route(
    "/refresh",
    methods=["POST"],
)
async def refresh(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/refresh")


@router.api_route(
    "/forgot-password",
    methods=["POST"],
)
async def forgot_password(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/forgot-password")


@router.api_route(
    "/reset-password",
    methods=["POST"],
)
async def reset_password(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/reset-password")


@router.get("/verify-email")
async def verify_email(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/verify-email")


@router.post("/resend-verification")
async def resend_verification(request: Request):
    return await proxy_request(request, f"{AUTH_SERVICE_URL}/auth/resend-verification")


@router.get("/google")
async def google_login(request: Request):
    return await proxy_request(
        request,
        f"{AUTH_SERVICE_URL}/auth/google",
        follow_redirects=False,
    )


@router.get("/google/callback")
async def google_callback(request: Request):
    return await proxy_request(
        request,
        f"{AUTH_SERVICE_URL}/auth/google/callback",
        follow_redirects=False,
    )


@router.post("/google/complete")
async def google_complete(request: Request):
    return await proxy_request(
        request,
        f"{AUTH_SERVICE_URL}/auth/google/complete",
    )


@router.post("/google/exchange")
async def google_exchange(request: Request):
    return await proxy_request(
        request,
        f"{AUTH_SERVICE_URL}/auth/google/exchange",
    )