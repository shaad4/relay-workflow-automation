from fastapi import FastAPI


app = FastAPI(
    title="Relay API Gateway",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
    }