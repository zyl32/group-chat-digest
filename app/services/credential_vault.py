"""Credential vault backends for storing secrets.

Provides a Protocol-based abstraction over secret storage with two backends:
- InMemoryVault: ephemeral, in-process store (used for tests/dev)
- OSKeyringVault: backed by the OS keyring via the `keyring` library

The Protocol is runtime-checkable so the T19 credential router can dispatch
via isinstance checks (mirrors the LLMProvider pattern from T11).
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

import keyring
from keyring.errors import KeyringError

__all__ = ["CredentialVault", "InMemoryVault", "OSKeyringVault"]

_DEFAULT_SERVICE: Final[str] = "group-chat-digest"


@runtime_checkable
class CredentialVault(Protocol):
    """Abstract credential vault.

    Implementations store, retrieve, introspect, and clear named secrets.
    `status()` returns metadata only (never the plaintext value) so it is
    safe to surface in API responses or logs.
    """

    def store(self, key_name: str, value: str) -> None: ...
    def load(self, key_name: str) -> str | None: ...
    def status(self, key_name: str) -> dict[str, bool]: ...
    def clear(self, key_name: str) -> None: ...


class InMemoryVault:
    """Ephemeral in-process credential store.

    WARNING: NOT for production. Secrets reside as plaintext in process
    memory and may be exposed via core dumps, swap, or debugger attachment.
    Use `OSKeyringVault` for any deployment.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def store(self, key_name: str, value: str) -> None:
        self._store[key_name] = value

    def load(self, key_name: str) -> str | None:
        return self._store.get(key_name)

    def status(self, key_name: str) -> dict[str, bool]:
        return {"configured": key_name in self._store}

    def clear(self, key_name: str) -> None:
        self._store.pop(key_name, None)


class OSKeyringVault:
    """Credential vault backed by the OS keyring service.

    Production-recommended backend. Delegates to the `keyring` library;
    service name is configurable to allow multiple deployments on the same
    host without collision.

    `load()` returns a plaintext `str`; callers must clear references
    promptly and avoid logging the returned value.
    """

    def __init__(self, service: str = _DEFAULT_SERVICE) -> None:
        self.service = service

    def store(self, key_name: str, value: str) -> None:
        keyring.set_password(self.service, key_name, value)

    def load(self, key_name: str) -> str | None:
        return keyring.get_password(self.service, key_name)

    def status(self, key_name: str) -> dict[str, bool]:
        # Performs a get_password fetch solely to check presence; do not
        # call on hot paths — it materializes the secret into Python memory.
        return {
            "configured": keyring.get_password(self.service, key_name) is not None
        }

    def clear(self, key_name: str) -> None:
        try:
            keyring.delete_password(self.service, key_name)
        except (KeyringError, KeyError):
            # Key not present or backend refused — clear is idempotent.
            # KeyError covers keyring backends that surface raw KeyError
            # instead of the more specific PasswordDeleteError subclass.
            pass
