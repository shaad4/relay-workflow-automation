from fastapi import FastAPI


app = FastAPI(
    title="Relay Execution Service",
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "execution-service",
    }