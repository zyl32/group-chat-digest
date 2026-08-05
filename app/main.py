"""FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import credentials, digests, exports, health, todos, uploads

app = FastAPI(title="Group Chat Digest")
app.include_router(uploads.router)
app.include_router(digests.router)
app.include_router(todos.router)
app.include_router(exports.router)
app.include_router(credentials.router)
app.include_router(health.router)

_FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")


def _serve(name: str) -> FileResponse:
    """Serve a frontend HTML page by filename."""
    return FileResponse(_FRONTEND_DIR / name)


@app.get("/")
def index() -> FileResponse:
    return _serve("index.html")


@app.get("/setup.html")
def setup_page() -> FileResponse:
    return _serve("setup.html")


@app.get("/todos.html")
def todos_page() -> FileResponse:
    return _serve("todos.html")


@app.get("/digests.html")
def digests_page() -> FileResponse:
    return _serve("digests.html")


@app.get("/digest_detail.html")
def digest_detail_page() -> FileResponse:
    return _serve("digest_detail.html")


__all__ = ["app"]
