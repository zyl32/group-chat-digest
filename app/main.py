from fastapi import FastAPI

app = FastAPI(title="Group Chat Digest")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
