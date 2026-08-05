"""Tests for static frontend mounting and page serving."""

from fastapi.testclient import TestClient

from app.main import app


def test_index_html_served() -> None:
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Group Chat Digest" in r.text


def test_static_css_served() -> None:
    client = TestClient(app)
    r = client.get("/static/styles.css")
    assert r.status_code == 200
    assert "content-type" in r.headers
    assert r.headers["content-type"].startswith("text/css")


def test_setup_html_served() -> None:
    client = TestClient(app)
    r = client.get("/setup.html")
    assert r.status_code == 200
    assert "API" in r.text or "key" in r.text.lower() or "凭据" in r.text


def test_todos_html_served() -> None:
    client = TestClient(app)
    r = client.get("/todos.html")
    assert r.status_code == 200
    assert "Todo" in r.text or "待办" in r.text


def test_digests_html_served() -> None:
    client = TestClient(app)
    r = client.get("/digests.html")
    assert r.status_code == 200


def test_digest_detail_html_served() -> None:
    client = TestClient(app)
    r = client.get("/digest_detail.html")
    assert r.status_code == 200


def test_index_html_links_to_setup() -> None:
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert 'href="/setup.html"' in r.text or "href=\"/setup.html\"" in r.text


def test_index_html_has_upload_form() -> None:
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<form" in r.text
    assert "multipart/form-data" in r.text
