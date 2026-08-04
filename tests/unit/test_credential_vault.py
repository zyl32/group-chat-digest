"""Tests for CredentialVault backends (InMemory + OS keyring)."""

from app.services.credential_vault import (
    CredentialVault,
    InMemoryVault,
    OSKeyringVault,
)


def test_in_memory_store_load_status_clear():
    v = InMemoryVault()
    v.store("k", "secret")
    assert v.load("k") == "secret"
    assert v.status("k") == {"configured": True}
    v.clear("k")
    assert v.load("k") is None
    assert v.status("k") == {"configured": False}


def test_status_never_returns_plaintext():
    v = InMemoryVault()
    v.store("k", "secret")
    result = v.status("k")
    assert "secret" not in str(result)


def test_os_keyring_with_mock(monkeypatch):
    fake_store: dict[tuple[str, str], str] = {}

    class FakeKeyring:
        def set_password(self, s, u, p): fake_store[(s, u)] = p
        def get_password(self, s, u): return fake_store.get((s, u))
        def delete_password(self, s, u): fake_store.pop((s, u), None)

    monkeypatch.setattr("app.services.credential_vault.keyring", FakeKeyring())
    v = OSKeyringVault(service="test-app")
    v.store("k", "secret")
    assert v.load("k") == "secret"
    assert v.status("k") == {"configured": True}
    v.clear("k")
    assert v.load("k") is None


def test_in_memory_status_after_clear():
    """clear() is idempotent — calling twice must not raise."""
    v = InMemoryVault()
    v.store("k", "secret")
    v.clear("k")
    v.clear("k")  # second clear on missing key
    assert v.load("k") is None
    assert v.status("k") == {"configured": False}


def test_os_keyring_clear_idempotent(monkeypatch):
    """Deleting a non-existent key must not raise."""
    class FakeKeyring:
        def set_password(self, s, u, p): raise AssertionError("should not be called")
        def get_password(self, s, u): return None
        def delete_password(self, s, u):
            raise KeyError("not found")

    monkeypatch.setattr("app.services.credential_vault.keyring", FakeKeyring())
    v = OSKeyringVault(service="test-app")
    v.clear("missing-key")  # should not raise
    assert v.load("missing-key") is None


def test_credential_vault_isinstance_runtime_checkable():
    """Protocol should be runtime-checkable for T19 router isinstance checks."""
    assert isinstance(InMemoryVault(), CredentialVault)
    assert isinstance(OSKeyringVault(service="x"), CredentialVault)


def test_os_keyring_load_missing(monkeypatch):
    """load() on a non-existent key must return None (not raise)."""
    class FakeKeyring:
        def set_password(self, s, u, p): raise AssertionError("should not be called")
        def get_password(self, s, u): return None
        def delete_password(self, s, u): raise AssertionError("should not be called")

    monkeypatch.setattr("app.services.credential_vault.keyring", FakeKeyring())
    assert OSKeyringVault(service="x").load("absent") is None
