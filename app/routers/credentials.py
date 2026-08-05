"""Credential router — first-run setup and key management.

Endpoints:
- GET  /api/credentials/{key_name}/status  → {"configured": bool}
- POST /api/credentials/{key_name}         → {"stored": bool}  (body: {"value": str})
- DELETE /api/credentials/{key_name}        → {"cleared": bool}

Security invariants:
- ``status()`` NEVER returns the plaintext value, length, or any hint beyond
  the boolean ``configured`` flag. This preserves the §3.1 constraint
  "查看状态时不得回显明文" and prevents side-channel enumeration.
- ``store()`` body must be ``{"value": <non-empty str>}`` — Pydantic with
  ``extra="forbid"`` + ``min_length=1`` rejects unknown fields and empty
  values at the 422 layer, before the vault is touched.
- ``key_name`` must be in ``_ALLOWED_KEYS`` allowlist — prevents arbitrary
  key-name injection / vault pollution. Unknown names return 400 (client
  error: typo or injection attempt).
- The plaintext value is NEVER written to logs. ``logger.warning`` on the
  400 path logs the key_name only (key_name is not secret).
- Production uses ``OSKeyringVault``; tests override via
  ``monkeypatch.setattr("app.routers.credentials.get_vault", ...)``.
"""

import logging
from typing import Final

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.credential_vault import CredentialVault, OSKeyringVault

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/credentials")

# Allowlist of recognized credential names. Prevents arbitrary key_name
# injection from polluting the OS keyring with attacker-chosen names.
# Extend this set when adding new secret-backed integrations (e.g. a second
# LLM provider) — never accept arbitrary caller-supplied names.
_ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"llm_api_key"})


class StoreRequest(BaseModel):
    """Request body for the store endpoint.

    ``extra="forbid"`` rejects unknown fields (prevents prompt drift / extra
    metadata smuggling). ``min_length=1`` rejects empty-string values at
    the Pydantic 422 layer before the vault is touched.
    """

    model_config = ConfigDict(extra="forbid")
    value: str = Field(..., min_length=1)


_vault: CredentialVault | None = None


def get_vault() -> CredentialVault:
    """Return the process-wide vault singleton (OSKeyringVault by default).

    Lazily constructed so tests that override via
    ``monkeypatch.setattr("app.routers.credentials.get_vault", ...)``
    never trigger an actual keyring access.
    """
    global _vault
    if _vault is None:
        _vault = OSKeyringVault()
    return _vault


def _validate_key_name(key_name: str) -> None:
    """Reject key_name not in the allowlist with 400.

    Logs key_name (NOT secret) at WARNING for audit trail of injection
    attempts. The key_name itself is not sensitive — it is a public
    allowlisted identifier — so logging it is safe.
    """
    if key_name not in _ALLOWED_KEYS:
        logger.warning("rejected unknown credential key_name: %s", key_name)
        raise HTTPException(400, f"unknown credential key: {key_name}")


@router.get("/{key_name}/status")
def status(key_name: str) -> dict[str, bool]:
    """Return ``{"configured": bool}`` for the named credential.

    Never returns the plaintext value, length, prefix, or any other
    metadata. The vault's ``status()`` enforces this contract; the router
    passes through unchanged.
    """
    _validate_key_name(key_name)
    return get_vault().status(key_name)


@router.post("/{key_name}")
def store(key_name: str, body: StoreRequest) -> dict[str, bool]:
    """Store the plaintext value under ``key_name``.

    SECURITY: ``body.value`` must never appear in any log line. The router
    intentionally does not log the value, the value's length, or any
    prefix-derived hint. Audit trail coverage is via ``test_store_does_not_log_value``.
    """
    _validate_key_name(key_name)
    get_vault().store(key_name, body.value)
    return {"stored": True}


@router.delete("/{key_name}")
def clear(key_name: str) -> dict[str, bool]:
    """Clear the named credential. Idempotent.

    T13's ``OSKeyringVault.clear()`` catches ``KeyringError``/``KeyError``
    silently so repeated DELETE on the same key returns 200 always.
    """
    _validate_key_name(key_name)
    get_vault().clear(key_name)
    return {"cleared": True}


__all__ = ["router", "get_vault", "store", "clear", "status", "StoreRequest"]
