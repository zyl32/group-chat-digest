"""Health-check router."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


__all__ = ["router"]
