import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import allowed_origins as configured_origins
from app.config import validate_startup
from app.grpc.server import start_grpc_server
from app.routes.auth import router as auth_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
    grpc_server = await start_grpc_server()

    try:
        yield
    finally:
        await grpc_server.stop(grace=5)


app = FastAPI(
    title="Relay Auth Service",
    lifespan=lifespan,
)

allowed_origins = set(configured_origins())

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
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
        origin_is_untrusted = origin and origin.rstrip("/") not in allowed_origins
        fetch_is_cross_site = not origin and fetch_site == "cross-site"
        if origin_is_untrusted or fetch_is_cross_site:
            return JSONResponse(
                status_code=403,
                content={"detail": "Untrusted request origin"},
            )
    return await call_next(request)


app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/live", include_in_schema=False)
async def liveness():
    """Process-only probe; dependency outages must not cause restart storms."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def readiness():
    """Bounded DB probe; no schema mutation or dependency details in responses."""
    from sqlalchemy import text

    from app.db.database import engine

    try:
        async with asyncio.timeout(3):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
