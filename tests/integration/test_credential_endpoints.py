"""Integration tests for the credential router (T19).

Covers the first-run setup endpoints:
- GET  /api/credentials/{key_name}/status  → {"configured": bool}
- POST /api/credentials/{key_name}          → {"stored": bool}
- DELETE /api/credentials/{key_name}        → {"cleared": bool}

Security invariants asserted here:
- ``status()`` NEVER returns the plaintext value (no length, no hint).
- The plaintext value is NEVER written to logs (caplog scan).
- ``key_name`` is allowlisted — unknown names return 400 (prevents vault
  pollution / enumeration).
- ``store()`` body is ``{"value": <non-empty str>}`` only — Pydantic with
  ``extra="forbid"`` + ``min_length=1`` rejects unknown fields and empty
  values at the 422 layer.
- ``clear()`` is idempotent — DELETE on an unconfigured key returns 200.
"""

import logging

from app.services.credential_vault import InMemoryVault


def test_status_unconfigured(client, monkeypatch):
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    r = client.get("/api/credentials/llm_api_key/status")
    assert r.status_code == 200
    assert r.json() == {"configured": False}


def test_store_then_status_configured(client, monkeypatch):
    v = InMemoryVault()
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    r = client.post("/api/credentials/llm_api_key", json={"value": "sk-test"})
    assert r.status_code == 200
    assert r.json() == {"stored": True}
    s = client.get("/api/credentials/llm_api_key/status").json()
    assert s == {"configured": True}


def test_clear(client, monkeypatch):
    v = InMemoryVault()
    v.store("llm_api_key", "sk-test")
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    r = client.delete("/api/credentials/llm_api_key")
    assert r.status_code == 200
    assert r.json() == {"cleared": True}
    assert client.get("/api/credentials/llm_api_key/status").json() == {"configured": False}


def test_status_does_not_leak_value(client, monkeypatch):
    v = InMemoryVault()
    v.store("llm_api_key", "sk-supersecret")
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    r = client.get("/api/credentials/llm_api_key/status")
    assert b"supersecret" not in r.content


def test_store_with_extra_field_returns_422(client, monkeypatch):
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    r = client.post(
        "/api/credentials/llm_api_key",
        json={"value": "sk-test", "extra": "x"},
    )
    assert r.status_code == 422


def test_store_missing_value_returns_422(client, monkeypatch):
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    r = client.post("/api/credentials/llm_api_key", json={})
    assert r.status_code == 422


def test_store_empty_value_returns_422(client, monkeypatch):
    """Empty string is rejected via Pydantic ``min_length=1`` → 422.

    Chosen 422 over 400 because empty-value is a request-body validation
    failure (Pydantic layer), consistent with extra-field / missing-field
    behavior. 400 is reserved for semantically invalid path params
    (unknown key_name).
    """
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    r = client.post("/api/credentials/llm_api_key", json={"value": ""})
    assert r.status_code == 422


def test_unknown_key_name_returns_400(client, monkeypatch):
    """Unknown key_name returns 400 (not 422/404).

    Why 400: key_name is a path parameter, not a body field, so Pydantic
    cannot reject it pre-flight. The allowlist check is application logic
    that prevents arbitrary key-name injection / vault pollution. 400
    (client error) signals the request was syntactically valid but
    semantically rejected.
    """
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    r = client.get("/api/credentials/random_key/status")
    assert r.status_code == 400


def test_status_response_shape_exactly_configured_only(client, monkeypatch):
    """Even when configured, response is exactly {"configured": True}.

    No value, no length, no metadata hint beyond the boolean. This is the
    §3.1 invariant "查看状态时不得回显明文" — extended to "回显任何可能
    泄露信息" (length, prefix, etc.).
    """
    v = InMemoryVault()
    v.store("llm_api_key", "sk-supersecret")
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    r = client.get("/api/credentials/llm_api_key/status")
    assert r.status_code == 200
    assert list(r.json().keys()) == ["configured"]
    assert r.json() == {"configured": True}


def test_store_does_not_log_value(client, monkeypatch, caplog):
    """The plaintext value must never appear in any log record.

    Asserts against the §3.1 invariant "绝不写入日志". Captures the router
    logger at DEBUG level (the vault backend ``InMemoryVault`` does not
    log, so router coverage is sufficient for this test's mock setup).
    """
    v = InMemoryVault()
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    secret = "sk-DO-NOT-LOG-THIS-VALUE"
    with caplog.at_level(logging.DEBUG, logger="app.routers.credentials"):
        r = client.post("/api/credentials/llm_api_key", json={"value": secret})
    assert r.status_code == 200
    for record in caplog.records:
        assert secret not in record.getMessage()
        # Also check formatted args — record.getMessage renders the template
        # with args, so this covers both static and parameterized log lines.


def test_store_then_clear_then_status_unconfigured(client, monkeypatch):
    """Full lifecycle: store → status configured → clear → status unconfigured."""
    v = InMemoryVault()
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    assert client.get("/api/credentials/llm_api_key/status").json() == {
        "configured": False
    }
    assert client.post(
        "/api/credentials/llm_api_key", json={"value": "sk-test"}
    ).json() == {"stored": True}
    assert client.get("/api/credentials/llm_api_key/status").json() == {
        "configured": True
    }
    assert client.delete("/api/credentials/llm_api_key").json() == {"cleared": True}
    assert client.get("/api/credentials/llm_api_key/status").json() == {
        "configured": False
    }


def test_clear_idempotent_on_unconfigured(client, monkeypatch):
    """DELETE on a key with no stored value returns 200 (clear is idempotent).

    T13's OSKeyringVault.clear() catches KeyringError/KeyError silently;
    the router must preserve that idempotency contract — repeated DELETE
    of the same key must not surface a 404/500.
    """
    v = InMemoryVault()
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: v)
    r = client.delete("/api/credentials/llm_api_key")
    assert r.status_code == 200
    assert r.json() == {"cleared": True}
    # Second delete on the same (still unconfigured) key
    r2 = client.delete("/api/credentials/llm_api_key")
    assert r2.status_code == 200
    assert r2.json() == {"cleared": True}


def test_unknown_key_name_rejected_on_all_verbs(client, monkeypatch):
    """Allowlist applies to status / store / clear — not just status.

    Prevents an attacker from probing arbitrary key names across verbs.
    """
    monkeypatch.setattr("app.routers.credentials.get_vault", lambda: InMemoryVault())
    assert client.get("/api/credentials/evil_key/status").status_code == 400
    assert client.post(
        "/api/credentials/evil_key", json={"value": "x"}
    ).status_code == 400
    assert client.delete("/api/credentials/evil_key").status_code == 400
