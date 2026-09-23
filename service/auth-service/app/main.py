from fastapi import FastAPI

app = FastAPI(title="Relay Auth Service")

@app.get("/health")
def health_check():
    return {"status": "ok"}