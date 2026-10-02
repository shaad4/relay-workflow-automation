import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.public_auth import router as public_auth_router
from app.routes.workflows import router as workflows_router

from app.routes.integration import router as integration_router
from app.routes.public_webhooks import router as public_webhooks_router

from app.routes.connections import router as connections_router

load_dotenv()

app = FastAPI(
    title="Relay API Gateway",
    version="1.0.0",
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [frontend_url]
if "localhost" in frontend_url:
    allowed_origins.append(frontend_url.replace("localhost", "127.0.0.1"))
elif "127.0.0.1" in frontend_url:
    allowed_origins.append(frontend_url.replace("127.0.0.1", "localhost"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_cookie_origin(request: Request, call_next):
    if (
        request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}
        and (
            request.cookies.get("relay_access_token")
            or request.cookies.get("relay_refresh_token")
        )
    ):
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        origin_is_untrusted = origin and origin.rstrip("/") not in {
            configured.rstrip("/") for configured in allowed_origins
        }
        fetch_is_cross_site = not origin and fetch_site == "cross-site"
        if origin_is_untrusted or fetch_is_cross_site:
            return JSONResponse(
                status_code=403,
                content={"detail": "Untrusted request origin"},
            )
    return await call_next(request)

app.include_router(auth_router)
app.include_router(public_auth_router)
app.include_router(workflows_router)
app.include_router(integration_router)
app.include_router(public_webhooks_router)
app.include_router(connections_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
    }
