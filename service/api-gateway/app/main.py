import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.public_auth import router as public_auth_router
from app.routes.workflows import router as workflows_router

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

app.include_router(auth_router)
app.include_router(public_auth_router)
app.include_router(workflows_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
    }


