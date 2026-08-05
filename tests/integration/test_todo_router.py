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
