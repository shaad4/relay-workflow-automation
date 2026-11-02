from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import allowed_origins as configured_origins
from app.config import validate_startup
from app.core.proxy import public_redirect_location
from app.routes.ai.knowledge_bases import router as knowledge_base_router
from app.routes.ai.provider_connections import router as ai_provider_connections_router
from app.routes.auth.authenticated import router as auth_router
from app.routes.auth.public import router as public_auth_router
from app.routes.dashboard.overview import router as dashboard_router
from app.routes.executions.approvals import router as approvals_router
from app.routes.executions.dead_letter import router as dead_letter_router
from app.routes.executions.executions import router as executions_router
from app.routes.integrations.connections import router as connections_router
from app.routes.integrations.public_webhooks import router as public_webhooks_router
from app.routes.integrations.webhooks import router as integration_router
from app.routes.workflows.manual_triggers import router as manual_triggers_router
from app.routes.workflows.schedules import router as schedules_router
from app.routes.workflows.workflows import router as workflows_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
    yield


app = FastAPI(
    title="Relay API Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = configured_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_cookie_origin(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"} and (
        request.cookies.get("relay_access_token") or request.cookies.get("relay_refresh_token")
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
    response = await call_next(request)
    if "location" in response.headers:
        response.headers["location"] = public_redirect_location(response.headers["location"])
    return response


app.include_router(auth_router)
app.include_router(public_auth_router)
app.include_router(workflows_router)
app.include_router(integration_router)
app.include_router(public_webhooks_router)
app.include_router(connections_router)
app.include_router(approvals_router)
app.include_router(knowledge_base_router)
app.include_router(ai_provider_connections_router)
app.include_router(manual_triggers_router)
app.include_router(schedules_router)
app.include_router(executions_router)
app.include_router(dead_letter_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
    }


app.include_router(dashboard_router)


@app.get("/health/live", include_in_schema=False)
async def liveness():
    """Process-only probe; dependency outages must not cause restart storms."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def readiness():
    """Gateway startup validates configuration; upstreams have their own probes."""
    return {"status": "ready"}
