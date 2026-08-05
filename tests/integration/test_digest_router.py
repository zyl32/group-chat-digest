"""Tests for GET /api/digests — list all digests, most recent first."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.digest import Digest


def _make_digest(
    *,
    upload_id: str,
    created_at: datetime,
    summary_blocks: list[dict] | None = None,
) -> Digest:
    return Digest(
        upload_id=upload_id,
        date=created_at.strftime("%Y-%m-%d"),
        window="24h",
        summary_blocks=summary_blocks or [{"topic": "t", "summary": "s", "msg_range": [0, 0]}],
        model_used="mock",
        created_at=created_at,
    )


def test_list_digests_empty(client, in_memory_db):
    r = client.get("/api/digests")
    assert r.status_code == 200
    assert r.json() == []


def test_list_digests_ordered_by_created_at_desc(client, in_memory_db):
    older = _make_digest(
        upload_id="u-old",
        created_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    newer = _make_digest(
        upload_id="u-new",
        created_at=datetime(2026, 8, 5, 10, 0, 0, tzinfo=timezone.utc),
    )
    in_memory_db.add_all([older, newer])
    in_memory_db.commit()

    r = client.get("/api/digests")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["upload_id"] == "u-new"
    assert data[1]["upload_id"] == "u-old"


def test_list_digests_response_shape_matches_get_digest(client, in_memory_db):
    d = _make_digest(
        upload_id="u-shape",
        created_at=datetime(2026, 8, 5, 10, 0, 0, tzinfo=timezone.utc),
        summary_blocks=[{"topic": "DDL", "summary": "明天交报告", "msg_range": [0, 2]}],
    )
    in_memory_db.add(d)
    in_memory_db.commit()

    r = client.get("/api/digests")
    assert r.status_code == 200
    item = r.json()[0]
    assert set(item.keys()) == {
        "id",
        "upload_id",
        "date",
        "window",
        "summary_blocks",
        "model_used",
    }
    assert item["upload_id"] == "u-shape"
    assert item["model_used"] == "mock"
    assert item["summary_blocks"] == [
        {"topic": "DDL", "summary": "明天交报告", "msg_range": [0, 2]}
    ]
