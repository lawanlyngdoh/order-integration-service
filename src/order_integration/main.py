from fastapi import FastAPI

app = FastAPI(
    title="Order Integration Service",
    version="0.1.0",
)


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}