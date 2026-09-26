from fastapi import FastAPI

app = FastAPI(title="Relay Workflow Service")

@app.get("/health")
async def health_check():
    return{"status": "ok", "service": "workflow-service"}