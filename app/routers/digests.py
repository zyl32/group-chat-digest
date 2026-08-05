"""Digest router — list all digests, most recent first."""

import logging
from typing import Any, Iterator

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.digest import Digest
from app.routers.uploads import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/digests")


@router.get("")
def list_digests(session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List all digests ordered by ``created_at`` descending.

    Response shape mirrors :func:`app.routers.uploads.get_digest`
    (``id`` / ``upload_id`` / ``date`` / ``window`` / ``summary_blocks``
    / ``model_used``). An empty store yields ``[]`` with HTTP 200.
    """
    rows = (
        session.query(Digest).order_by(Digest.created_at.desc()).all()
    )
    return [
        {
            "id": d.id,
            "upload_id": d.upload_id,
            "date": d.date,
            "window": d.window,
            "summary_blocks": d.summary_blocks,
            "model_used": d.model_used,
        }
        for d in rows
    ]


__all__ = ["router", "list_digests"]
