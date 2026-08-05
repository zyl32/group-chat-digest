"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.routers import credentials, exports, health, todos, uploads

app = FastAPI(title="Group Chat Digest")
app.include_router(uploads.router)
app.include_router(todos.router)
app.include_router(exports.router)
app.include_router(credentials.router)
app.include_router(health.router)


__all__ = ["app"]
