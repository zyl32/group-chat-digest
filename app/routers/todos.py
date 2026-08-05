"""Todo router — list todos and apply state machine transitions."""

import logging
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.routers.uploads import get_db
from app.services.todo_state import IllegalTransition, TodoStateMachine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/todos")
_sm = TodoStateMachine()


class ActionRequest(BaseModel):
    """Request body for the state transition endpoint."""

    model_config = ConfigDict(extra="forbid")

    action: str


@router.get("")
def list_todos(session: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List all todos with key fields (no message bodies)."""
    rows = session.query(Todo).all()
    return [
        {
            "id": t.id,
            "what": t.what,
            "who": t.who,
            "due_at": t.due_at.isoformat() if t.due_at else None,
            "state": t.state,
        }
        for t in rows
    ]


@router.post("/{todo_id}/action")
def perform_action(
    todo_id: int,
    body: ActionRequest,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Apply a state machine action to a todo.

    Returns 200 with new state on success, 404 if todo missing, 409 if the
    transition is illegal (e.g., done -> reactivate is not allowed).
    """
    t = session.get(Todo, todo_id)
    if t is None:
        raise HTTPException(404)
    try:
        t.state = _sm.transition(t.state, body.action)
    except IllegalTransition as e:
        logger.warning(
            "illegal transition todo_id=%s state=%s action=%s",
            todo_id, t.state, body.action,
        )
        raise HTTPException(409, "illegal state transition") from e
    session.flush()
    return {"id": t.id, "state": t.state}


__all__ = ["router", "perform_action", "list_todos", "ActionRequest"]
