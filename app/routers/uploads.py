"""Upload router — accept chat export files and persist parsed messages.

Deviation from PLAN spec: ``fmt`` is **optional** (``Form(None)``) rather
than required. This is required so ``test_upload_too_large`` — which posts
only a file (no ``fmt`` field) — can reach the size check and return 413
instead of being short-circuited by FastAPI's form validation (422). With
``fmt`` optional, a missing ``fmt`` falls through to :func:`parse_upload`,
which raises ``ParseError("unknown format: None")`` → 422, satisfying
``test_upload_unknown_format``.
"""

import logging
import os
import uuid
from typing import Any, Iterator, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.adapters.llm_provider import get_provider
from app.adapters.parsers import ParseError
from app.adapters.parsers.base import ParsedMessage
from app.config import AppConfig, load_config
from app.models.db import Base, get_engine, get_session
from app.models.digest import Digest
from app.models.message import Message
from app.models.todo import Todo
from app.models.upload import Upload
from app.services.digest import DigestService
from app.services.parser_service import parse_upload
from app.services.todo import TodoExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads")
cfg: AppConfig = load_config()

_MAX_FILENAME_LEN = 255


def _sanitize_filename(name: str | None) -> str:
    """Strip directory traversal / NUL bytes; return a safe basename."""
    cleaned = os.path.basename(name or "")[:_MAX_FILENAME_LEN]
    return cleaned or "upload.bin"


def get_db() -> Iterator[Session]:
    """Production DB dependency. Tests override via ``app.dependency_overrides``."""
    engine = get_engine(cfg.db.url)
    # TODO(T17): move schema creation to app startup; per-request create_all is wasteful.
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
    max_bytes = cfg.upload.max_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1 << 20):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, "file too large")
        chunks.append(chunk)
    raw = b"".join(chunks)

    upload_id = str(uuid.uuid4())
    safe_filename = _sanitize_filename(file.filename)
    fmt_norm = (fmt or "").lower()
    # Synchronous parse (T17 will switch to scheduler async).
    try:
        msgs = parse_upload(raw, fmt_norm)
    except ParseError as e:
        logger.warning("parse failed: %s", e)
        raise HTTPException(422, "unsupported or malformed chat export") from e
    u = Upload(
        id=upload_id,
        filename=safe_filename,
        fmt=fmt_norm,
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


@router.post("/{upload_id}/process")
def process_upload(
    upload_id: str,
    llm_name: str = "mock",
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Trigger digest + todo extraction for an already-uploaded set of messages.

    Args:
        upload_id: The upload to process.
        llm_name: Provider name (default ``"mock"``). Tests override via
            ``monkeypatch.setattr("app.routers.uploads.get_provider", ...)``
            to return a pre-programmed MockLLMAdapter fixture.

    Returns:
        ``{"digest_id": int, "todo_count": int}`` on success.

    Raises:
        HTTPException: 404 if the upload or its messages are missing;
            400 if a digest already exists for this upload (idempotency:
            v1 does not support re-processing — callers must upload a
            new file to retry).
    """
    u = session.get(Upload, upload_id)
    if u is None:
        logger.warning("process: upload not found upload_id=%s", upload_id)
        raise HTTPException(404, "upload not found")
    existing = session.query(Digest).filter(Digest.upload_id == upload_id).first()
    if existing is not None:
        logger.warning("process: already processed upload_id=%s", upload_id)
        raise HTTPException(400, "upload already processed; use a new upload to retry")

    rows = session.query(Message).filter(Message.upload_id == upload_id).all()
    if not rows:
        logger.warning("process: no messages for upload_id=%s", upload_id)
        raise HTTPException(404, "no messages found for upload")
    msgs = [
        ParsedMessage(
            sender=r.sender,
            content=r.content,
            timestamp=r.timestamp,
            msg_id=r.msg_id or f"m{r.id}",
        )
        for r in rows
    ]

    llm = get_provider(llm_name)
    digest = DigestService(llm=llm, session=session).generate(upload_id, msgs)
    TodoExtractor(llm=llm, session=session).extract(
        upload_id, msgs, digest.summary_blocks
    )
    todo_count = (
        session.query(Todo).filter(Todo.upload_id == upload_id).count()
    )
    return {"digest_id": digest.id, "todo_count": todo_count}


@router.get("/{upload_id}/digest")
def get_digest(upload_id: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the persisted digest for an upload.

    Raises:
        HTTPException: 404 if no digest exists for this upload_id.
    """
    d = session.query(Digest).filter(Digest.upload_id == upload_id).first()
    if d is None:
        logger.warning("get_digest: no digest for upload_id=%s", upload_id)
        raise HTTPException(404, "digest not found for upload")
    return {
        "id": d.id,
        "upload_id": d.upload_id,
        "date": d.date,
        "window": d.window,
        "summary_blocks": d.summary_blocks,
        "model_used": d.model_used,
    }


__all__ = [
    "router",
    "get_db",
    "create_upload",
    "get_status",
    "process_upload",
    "get_digest",
]
