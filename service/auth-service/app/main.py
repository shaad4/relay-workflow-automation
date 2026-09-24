from fastapi import FastAPI
from app.routes.auth import router as auth_router

app = FastAPI(title="Relay Auth Service")

app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}