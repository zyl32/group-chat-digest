"""Export router — export todos as ICS or Todoist quick-add URLs."""

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.routers.uploads import get_db
from app.services.export import build_todoist_url, export_ics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exports")

_NOT_FOUND_MSG = "no todos found for given ids"


class ExportRequest(BaseModel):
    """Request body for the export endpoint."""

    model_config = ConfigDict(extra="forbid")

    todo_ids: list[int]
    format: Literal["ics", "todoist_url"]


def _normalize_dt(dt: datetime | None) -> datetime | None:
    """Normalize a datetime to tz-aware UTC.

    Naive datetimes are assumed to be UTC (mirrors T17 ``_serialize_dt``);
    tz-aware datetimes are converted to UTC. Returns ``None`` if ``dt`` is
    ``None``. Required because :func:`export_ics` raises ``ValueError`` on
    naive datetimes.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_todos(session: Session, todo_ids: list[int]) -> list[Todo]:
    """Fetch todos by id; raise 404 if any requested id is missing.

    Empty ``todo_ids`` returns ``[]`` (caller handles empty-list semantics).
    """
    if not todo_ids:
        return []
    rows = session.query(Todo).filter(Todo.id.in_(todo_ids)).all()
    if not rows:
        raise HTTPException(404, _NOT_FOUND_MSG)
    return rows


def _to_export_dicts(rows: list[Todo]) -> list[dict[str, Any]]:
    """Project Todo rows into the dict shape expected by export_ics/build_todoist_url."""
    return [
        {
            "what": t.what,
            "who": t.who,
            "due_at": _normalize_dt(t.due_at),
        }
        for t in rows
    ]


@router.post("", response_model=None)
def create_export(
    body: ExportRequest,
    session: Session = Depends(get_db),
) -> Response | dict[str, Any]:
    """Export todos as ICS (``text/calendar``) or Todoist URL (JSON).

    Empty ``todo_ids`` returns 200 with an empty VCALENDAR (asking for
    nothing yields nothing). Requesting IDs that don't exist returns 404.
    Unknown ``format`` values are rejected by Pydantic with 422.
    """
    rows = _load_todos(session, body.todo_ids)
    todos_data = _to_export_dicts(rows)
    if body.format == "ics":
        return Response(content=export_ics(todos_data), media_type="text/calendar")
    return {"url": build_todoist_url(todos_data)}


__all__ = ["router", "create_export", "ExportRequest", "build_todoist_url"]
