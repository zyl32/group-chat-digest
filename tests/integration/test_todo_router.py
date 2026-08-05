from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.todo import Todo


def test_get_todos(client, in_memory_db):
    t = Todo(id=1, upload_id="u1", what="test", state="pending")
    in_memory_db.add(t)
    in_memory_db.commit()
    r = client.get("/api/todos")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_transition_pending_to_done(client, in_memory_db):
    t = Todo(id=1, upload_id="u1", what="test", state="pending")
    in_memory_db.add(t)
    in_memory_db.commit()
    r = client.post("/api/todos/1/action", json={"action": "done"})
    assert r.status_code == 200
    assert r.json()["state"] == "done"


def test_illegal_transition_returns_409(client, in_memory_db):
    t = Todo(id=1, upload_id="u1", what="test", state="done")
    in_memory_db.add(t)
    in_memory_db.commit()
    r = client.post("/api/todos/1/action", json={"action": "reactivate"})
    assert r.status_code == 409


def test_get_todos_empty(client, in_memory_db):
    r = client.get("/api/todos")
    assert r.status_code == 200
    assert r.json() == []


def test_action_unknown_todo_returns_404(client, in_memory_db):
    r = client.post("/api/todos/999/action", json={"action": "done"})
    assert r.status_code == 404


def test_action_unknown_action_returns_400(client, in_memory_db):
    """An action not in TodoStateMachine.known_actions() returns 400, not 409."""
    t = Todo(id=1, upload_id="u1", what="test", state="pending")
    in_memory_db.add(t)
    in_memory_db.commit()
    r = client.post("/api/todos/1/action", json={"action": "garbage"})
    assert r.status_code == 400


def test_list_todos_serializes_naive_datetime_as_utc(client, in_memory_db):
    """A naive due_at (e.g., from datetime.fromisoformat('2026-08-10')) serializes as UTC ISO."""
    t = Todo(
        id=1,
        upload_id="u1",
        what="test",
        state="pending",
        due_at=datetime(2026, 8, 10, 0, 0, 0),  # naive
    )
    in_memory_db.add(t)
    in_memory_db.commit()
    r = client.get("/api/todos")
    assert r.status_code == 200
    due_at = r.json()[0]["due_at"]
    # Should end with +00:00 (UTC offset), not be a bare naive isoformat
    assert due_at.endswith("+00:00")
    # And the value should equal the same instant in UTC
    parsed = datetime.fromisoformat(due_at)
    assert parsed == datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)
