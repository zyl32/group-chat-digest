from datetime import datetime, timezone

from app.models.upload import Upload


def test_in_memory_db_fixture(in_memory_db):
    u = Upload(
        id="test-1",
        filename="t.json",
        fmt="wechat",
        size=1,
        status="received",
        received_at=datetime.now(timezone.utc),
    )
    in_memory_db.add(u)
    in_memory_db.commit()
    assert in_memory_db.query(Upload).count() == 1


def test_client_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
