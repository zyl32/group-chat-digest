"""Upload router — accept chat export files and persist parsed messages.

Deviation from PLAN spec: ``fmt`` is **optional** (``Form(None)``) rather
than required. This is required so ``test_upload_too_large`` — which posts
only a file (no ``fmt`` field) — can reach the size check and return 413
instead of being short-circuited by FastAPI's form validation (422). With
``fmt`` optional, a missing ``fmt`` falls through to :func:`parse_upload`,
which raises ``ParseError("unknown format: None")`` → 422, satisfying
``test_upload_unknown_format``.
"""

import uuid
from typing import Iterator, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.adapters.parsers import ParseError
from app.config import AppConfig, load_config
from app.models.db import Base, get_engine, get_session
from app.models.message import Message
from app.models.upload import Upload
from app.services.parser_service import parse_upload

router = APIRouter(prefix="/api/uploads")
cfg: AppConfig = load_config()


def get_db() -> Iterator[Session]:
    """Production DB dependency. Tests override via ``app.dependency_overrides``."""
    engine = get_engine(cfg.db.url)
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        yield session


@router.post("", status_code=202)
async def create_upload(
    file: UploadFile = File(...),
    fmt: Optional[str] = Form(None),
    session: Session = Depends(get_db),
) -> dict:
    """Accept an upload, parse synchronously, and persist messages.

    Returns ``{"upload_id": ..., "status": "done"}`` on success. Errors:
    413 (too large), 422 (unknown format / parse failure).
    """
    raw = await file.read()
    if len(raw) > cfg.upload.max_size_mb * 1024 * 1024:
        raise HTTPException(413, "file too large")
    upload_id = str(uuid.uuid4())
    # Synchronous parse (T17 will switch to scheduler async).
    try:
        msgs = parse_upload(raw, fmt or "")
    except ParseError as e:
        raise HTTPException(422, str(e)) from e
    u = Upload(
        id=upload_id,
        filename=file.filename,
        fmt=fmt or "",
        size=len(raw),
        status="done",
    )
    session.add(u)
    for m in msgs:
        session.add(
            Message(
                upload_id=upload_id,
                sender=m.sender,
                content=m.content,
                timestamp=m.timestamp,
                msg_id=m.msg_id,
            )
        )
    return {"upload_id": upload_id, "status": "done"}


@router.get("/{upload_id}/status")
def get_status(upload_id: str, session: Session = Depends(get_db)) -> dict:
    """Return upload status and persisted message count."""
    u = session.get(Upload, upload_id)
    if u is None:
        raise HTTPException(404)
    count = session.query(Message).filter(Message.upload_id == upload_id).count()
    return {"upload_id": upload_id, "status": u.status, "message_count": count}


__all__ = ["router", "get_db", "create_upload", "get_status"]
