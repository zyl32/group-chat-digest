from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_upload_json_accepted(client, in_memory_db, mock_llm):
    f = Path("tests/fixtures/wechat_sample.json").read_bytes()
    r = client.post(
        "/api/uploads",
        files={"file": ("t.json", f, "application/json")},
        data={"fmt": "wechat"},
    )
    assert r.status_code == 202
    upload_id = r.json()["upload_id"]
    # Poll status (no-op for sync parsing; status is already "done")
    for _ in range(10):
        s = client.get(f"/api/uploads/{upload_id}/status").json()
        if s["status"] in ("done", "failed"):
            break
    assert s["status"] == "done"
    assert s["message_count"] == 2


def test_upload_too_large(client):
    big = b"x" * (11 * 1024 * 1024)
    r = client.post(
        "/api/uploads",
        files={"file": ("big.json", big, "application/json")},
    )
    assert r.status_code == 413


def test_upload_unknown_format(client):
    r = client.post(
        "/api/uploads",
        files={"file": ("t.json", b"{}", "application/json")},
    )
    assert r.status_code in (422, 400)
