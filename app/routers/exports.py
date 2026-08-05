"""Export router — export todos as ICS or Todoist quick-add URLs."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.routers.uploads import get_db
from app.services.export import build_todoist_url, export_ics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exports")


class ExportRequest(BaseModel):
    """Request body for the export endpoint."""

    model_config = ConfigDict(extra="forbid")

    todo_ids: list[int]
    format: str


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


@router.post("", response_model=None)
def create_export(
    body: ExportRequest,
    session: Session = Depends(get_db),
) -> Response | dict[str, Any]:
    """Export todos as ICS (``text/calendar``) or Todoist URL (JSON).

    Empty ``todo_ids`` returns 200 with an empty VCALENDAR (asking for
    nothing yields nothing). Requesting IDs that don't exist returns 404.
    Unknown ``format`` values return 400.
    """
    if body.format == "ics":
        # Empty list short-circuits to an empty calendar — distinguish from
        # the "all IDs unknown" case, which is a 404.
        if not body.todo_ids:
            return Response(
                content=export_ics([]), media_type="text/calendar"
            )
        rows = (
            session.query(Todo).filter(Todo.id.in_(body.todo_ids)).all()
        )
        if not rows:
            raise HTTPException(404, "no todos found for given ids")
        todos_data = [
            {
                "what": t.what,
                "who": t.who,
                "due_at": _normalize_dt(t.due_at),
            }
            for t in rows
        ]
        return Response(content=export_ics(todos_data), media_type="text/calendar")

    if body.format == "todoist_url":
        rows = (
            session.query(Todo).filter(Todo.id.in_(body.todo_ids)).all()
        )
        if not rows and body.todo_ids:
            # Asked for specific IDs that don't exist → 404. An empty
            # ``todo_ids`` list is allowed: build a URL with no text.
            raise HTTPException(404, "no todos found for given ids")
        todos_data = [
            {
                "what": t.what,
                "who": t.who,
                "due_at": _normalize_dt(t.due_at),
            }
            for t in rows
        ]
        return {"url": build_todoist_url(todos_data)}

    logger.warning("unknown export format: %s", body.format)
    raise HTTPException(400, f"unknown format: {body.format}")


__all__ = ["router", "create_export", "ExportRequest", "build_todoist_url"]
