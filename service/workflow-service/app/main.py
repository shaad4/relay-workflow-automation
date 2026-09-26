from fastapi import Depends, FastAPI

from app.dependencies import get_current_identity
from app.routes.workflows import router as workflows_router


app = FastAPI(title="Relay Workflow Service")

app.include_router(workflows_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "workflow-service"}


@app.get("/protected-test")
async def protected_test(
    identity: dict = Depends(get_current_identity),
):
    return {
        "message": "Authentication successful",
        "user_id": identity["user_id"],
        "workspace_id": identity["workspace_id"],
    }