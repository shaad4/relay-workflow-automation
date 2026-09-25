import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}