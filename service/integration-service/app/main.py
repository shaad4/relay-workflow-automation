from fastapi import FastAPI


app = FastAPI(
    title="Relay Integration Service",
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "integration-service"}

