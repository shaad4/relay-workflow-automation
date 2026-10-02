from fastapi import FastAPI


app = FastAPI(
    title="Relay Action Service",
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "action-service",
    }
