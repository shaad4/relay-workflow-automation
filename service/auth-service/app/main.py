import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.grpc.server import start_grpc_server
from app.routes.auth import router as auth_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = await start_grpc_server()

    yield

    await grpc_server.stop(grace=5)


app = FastAPI(
    title="Relay Auth Service",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = {frontend_url.rstrip("/")}
if "localhost" in frontend_url:
    allowed_origins.add(frontend_url.replace("localhost", "127.0.0.1").rstrip("/"))
elif "127.0.0.1" in frontend_url:
    allowed_origins.add(frontend_url.replace("127.0.0.1", "localhost").rstrip("/"))


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
