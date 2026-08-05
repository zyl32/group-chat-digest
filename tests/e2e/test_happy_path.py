"""End-to-end happy path: upload → process → digest → todos → action → export.

This test wires together all backend pieces (T14 upload + T15/T16 services
+ T17 todos + T18 exports + T19 credentials) into a single flow that
mirrors a real user session.

The most important wrinkle: the spec's ``mock_llm.set_response`` programs
the test's fixture, but the ``process`` endpoint calls
``get_provider("mock")`` which constructs a *new* ``MockLLMAdapter`` — so
the programmed responses would never be seen. We patch
``app.routers.uploads.get_provider`` to return the test's fixture
instead. This keeps the endpoint's contract (LLM name lookup via the
registry) while letting the test inject deterministic responses.
"""

import json
from pathlib import Path

import pytest

from app.routers import credentials
from app.services.credential_vault import InMemoryVault


def _configure_credential(monkeypatch) -> InMemoryVault:
    """Install an InMemoryVault with a stored key under the credentials router.

    Returns the vault so callers can assert against it.
    """
    v = InMemoryVault()
    v.store("llm_api_key", "sk-mock")
    monkeypatch.setattr(credentials, "get_vault", lambda: v)
    return v


def _patch_get_provider(monkeypatch, mock_llm) -> None:
    """Replace ``app.routers.uploads.get_provider`` with one that returns mock_llm.

    The process endpoint imports ``get_provider`` at module load time, so
    monkeypatching the attribute on the module replaces the binding used by
    the endpoint. This is the documented test seam for the LLM factory.
    """
    monkeypatch.setattr(
        "app.routers.uploads.get_provider",
        lambda name, **kwargs: mock_llm,
    )


def _upload_mock_file(client, filename: str = "mock_chat_with_todos.json"):
    """Upload a mock chat dataset and return the upload_id."""
    f = Path("data/mock", filename).read_bytes()
    r = client.post(
        "/api/uploads",
        files={"file": ("t.json", f, "application/json")},
        data={"fmt": "wechat"},
    )
    assert r.status_code == 202, r.text
    return r.json()["upload_id"]


def test_full_flow_with_mock_data(client, in_memory_db, mock_llm, monkeypatch):
    """Spec-driven happy path: upload → process → digest → todos → action → ICS."""
    _configure_credential(monkeypatch)

    mock_llm.set_response(
        "generate digest",
        json.dumps(
            {
                "blocks": [
                    {
                        "topic": "DDL",
                        "summary": "明天交报告",
                        "msg_range": [0, 2],
                    }
                ]
            }
        ),
    )
    mock_llm.set_response(
        "extract",
        json.dumps(
            {
                "todos": [
                    {
                        "who": "张三",
                        "what": "交报告",
                        "due_at": "2026-08-10",
                        "source_msg_id": 0,
                    }
                ]
            }
        ),
    )

    upload_id = _upload_mock_file(client)
    _patch_get_provider(monkeypatch, mock_llm)

    r = client.post(f"/api/uploads/{upload_id}/process", params={"llm_name": "mock"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "digest_id" in body
    assert body["todo_count"] >= 1

    r = client.get(f"/api/uploads/{upload_id}/digest")
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["summary_blocks"]) >= 1
    assert d["model_used"] == "mock"

    r = client.get("/api/todos")
    assert r.status_code == 200, r.text
    todos = r.json()
    assert any(t["what"] == "交报告" for t in todos)

    todo_id = todos[0]["id"]
    r = client.post(f"/api/todos/{todo_id}/action", json={"action": "done"})
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "done"

    r = client.post("/api/exports", json={"todo_ids": [todo_id], "format": "ics"})
    assert r.status_code == 200, r.text
    assert b"BEGIN:VCALENDAR" in r.content


def test_process_unknown_upload_returns_404(client, mock_llm, monkeypatch):
    """POST /api/uploads/{unknown}/process returns 404 (no upload row)."""
    _patch_get_provider(monkeypatch, mock_llm)
    r = client.post("/api/uploads/nonexistent/process", params={"llm_name": "mock"})
    assert r.status_code == 404, r.text


def test_process_idempotent_returns_400(client, mock_llm, monkeypatch):
    """Second call to /process returns 400 (digest already exists)."""
    _configure_credential(monkeypatch)
    mock_llm.set_response(
        "generate digest",
        json.dumps(
            {
                "blocks": [
                    {
                        "topic": "X",
                        "summary": "ok",
                        "msg_range": [0, 1],
                    }
                ]
            }
        ),
    )
    mock_llm.set_response(
        "extract",
        json.dumps({"todos": []}),
    )
    upload_id = _upload_mock_file(client)
    _patch_get_provider(monkeypatch, mock_llm)

    r1 = client.post(f"/api/uploads/{upload_id}/process", params={"llm_name": "mock"})
    assert r1.status_code == 200, r1.text

    r2 = client.post(f"/api/uploads/{upload_id}/process", params={"llm_name": "mock"})
    assert r2.status_code == 400, r2.text


def test_digest_unknown_upload_returns_404(client):
    """GET /api/uploads/{unknown}/digest returns 404."""
    r = client.get("/api/uploads/never-exists/digest")
    assert r.status_code == 404, r.text


def test_process_with_fallback_llm_still_succeeds(client, mock_llm, monkeypatch):
    """When LLM returns invalid JSON, services fall back; process still 200."""
    _configure_credential(monkeypatch)
    # Program the mock to return invalid JSON for both prompts.
    mock_llm.set_response("generate digest", "not-json-at-all")
    mock_llm.set_response("extract", "{ broken")

    upload_id = _upload_mock_file(client)
    _patch_get_provider(monkeypatch, mock_llm)

    r = client.post(f"/api/uploads/{upload_id}/process", params={"llm_name": "mock"})
    assert r.status_code == 200, r.text

    r = client.get(f"/api/uploads/{upload_id}/digest")
    assert r.status_code == 200, r.text
    blocks = r.json()["summary_blocks"]
    assert len(blocks) >= 1
    # Fallback block sentinel from DigestService.FALLBACK_BLOCK.
    assert any(b.get("topic") == "错误" for b in blocks)

    r = client.get("/api/todos")
    assert r.status_code == 200, r.text
    todos = r.json()
    # Fallback todos are "[待确认] ..." per TodoExtractor.
    assert any("待确认" in t["what"] for t in todos)
    # Fallback state is pending.
    assert all(t["state"] == "pending" for t in todos)


def test_full_flow_exports_ics_after_done_action(client, mock_llm, monkeypatch):
    """Full flow: export ICS after marking a todo done — VTODO is emitted.

    Note: the ICS exporter does not filter by state (it exports whatever
    the request lists), so we assert that the done todo's summary appears
    in the VTODO — verifying end-to-end data flow rather than ICS
    state-filtering behavior.
    """
    _configure_credential(monkeypatch)
    mock_llm.set_response(
        "generate digest",
        json.dumps(
            {
                "blocks": [
                    {
                        "topic": "作业",
                        "summary": "操作系统实验报告",
                        "msg_range": [0, 2],
                    }
                ]
            }
        ),
    )
    mock_llm.set_response(
        "extract",
        json.dumps(
            {
                "todos": [
                    {
                        "who": "张三",
                        "what": "操作系统实验报告",
                        "due_at": "2026-08-10",
                        "source_msg_id": 0,
                    }
                ]
            }
        ),
    )

    upload_id = _upload_mock_file(client)
    _patch_get_provider(monkeypatch, mock_llm)

    r = client.post(f"/api/uploads/{upload_id}/process", params={"llm_name": "mock"})
    assert r.status_code == 200, r.text

    r = client.get("/api/todos")
    todos = r.json()
    assert len(todos) == 1
    todo_id = todos[0]["id"]

    r = client.post(
        f"/api/todos/{todo_id}/action", json={"action": "done"}
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/api/exports", json={"todo_ids": [todo_id], "format": "ics"}
    )
    assert r.status_code == 200, r.text
    assert b"BEGIN:VCALENDAR" in r.content
    # ICS exporter uses VTODO (todos map to VTODO, not VEVENT).
    assert b"BEGIN:VTODO" in r.content
    # Summary should reflect the todo's "what" field.
    assert "操作系统实验报告".encode() in r.content
