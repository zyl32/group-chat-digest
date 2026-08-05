"""Integration tests for the export router (T18).

Covers:
- ICS export for existing todos (200, text/calendar).
- ICS export with empty ``todo_ids`` list (200, empty VCALENDAR) — asking for
  nothing should yield an empty calendar, not an error.
- ICS export when none of the requested IDs exist (404).
- Todoist URL export (200, JSON with ``url``).
- Unknown format (400).
- Naive ``due_at`` normalization to UTC (mirrors T17 ``_serialize_dt``).

Deviations from PLAN spec test snippets:
- ``content-type`` asserted via ``startswith("text/calendar")`` rather than
  ``==``: Starlette appends ``; charset=utf-8`` to text/* media types, so the
  exact-equality assertion in the spec is unachievable without bypassing
  Starlette's default header logic.
- Todoist URL assertions use ``unquote(url)`` to check for the Chinese
  task text: ``quote()`` percent-encodes non-ASCII per RFC 3986 (correct
  behavior), so the literal text won't appear in the raw URL.
"""

from datetime import datetime, timezone
from urllib.parse import unquote

from app.routers.exports import build_todoist_url
from app.models.todo import Todo


def test_export_ics_endpoint(client, in_memory_db):
    in_memory_db.add(
        Todo(id=1, upload_id="u1", what="交报告", who="张三", state="pending")
    )
    in_memory_db.commit()
    r = client.post("/api/exports", json={"todo_ids": [1], "format": "ics"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in r.content


def test_build_todoist_url():
    url = build_todoist_url([{"what": "交报告", "due_at": None}])
    assert "todoist.com" in url
    assert "交报告" in unquote(url)


def test_export_ics_empty_returns_200(client, in_memory_db):
    """Empty ``todo_ids`` list returns 200 with an empty (but valid) VCALENDAR.

    Asking for nothing should yield an empty calendar, not a 404 — a 404
    means "you asked for things that don't exist". An empty list asks for
    nothing, so we return an empty VCALENDAR.
    """
    r = client.post("/api/exports", json={"todo_ids": [], "format": "ics"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in r.content
    assert b"END:VCALENDAR" in r.content
    # No VTODO entries when no ids requested.
    assert b"BEGIN:VTODO" not in r.content


def test_export_ics_unknown_ids_returns_404(client, in_memory_db):
    """Requesting only IDs that don't exist returns 404."""
    r = client.post("/api/exports", json={"todo_ids": [999], "format": "ics"})
    assert r.status_code == 404


def test_export_todoist_url_format(client, in_memory_db):
    """``format="todoist_url"`` returns 200 JSON with ``url`` field."""
    in_memory_db.add(
        Todo(id=1, upload_id="u1", what="交报告", who="张三", state="pending")
    )
    in_memory_db.commit()
    r = client.post(
        "/api/exports", json={"todo_ids": [1], "format": "todoist_url"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "url" in body
    assert body["url"].startswith("https://todoist.com/")
    assert "交报告" in unquote(body["url"])


def test_export_unknown_format_returns_400(client, in_memory_db):
    """An unknown ``format`` value returns 400."""
    in_memory_db.add(
        Todo(id=1, upload_id="u1", what="交报告", who="张三", state="pending")
    )
    in_memory_db.commit()
    r = client.post(
        "/api/exports", json={"todo_ids": [1], "format": "garbage"}
    )
    assert r.status_code == 400


def test_export_ics_serializes_naive_due_at_as_utc(client, in_memory_db):
    """A naive ``due_at`` is normalized to UTC before being passed to ``export_ics``.

    ``export_ics`` raises ``ValueError`` on naive datetimes; the router must
    mirror T17's ``_serialize_dt`` pattern and assume naive == UTC.
    """
    in_memory_db.add(
        Todo(
            id=1,
            upload_id="u1",
            what="交报告",
            who="张三",
            state="pending",
            due_at=datetime(2026, 8, 10, 0, 0, 0),  # naive
        )
    )
    in_memory_db.commit()
    r = client.post("/api/exports", json={"todo_ids": [1], "format": "ics"})
    assert r.status_code == 200
    assert b"DTSTART:20260810T000000Z" in r.content
