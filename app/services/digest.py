"""DigestService: LLM-driven chat summarization with schema + fallback.

The service builds a prompt from parsed messages, calls the LLM provider,
validates the JSON response against `DigestResponse`, and persists a
`Digest` row. On JSON/ValidationError (or LLM exception after adapter
retries are exhausted) it falls back to a sentinel block rather than
raising — the upload pipeline must remain resilient to flaky LLM output.
Retry logic lives in the adapter (T11/T12), not here (YAGNI).
"""
import json
import logging
from datetime import datetime, timezone
from typing import Sequence

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.llm_provider import LLMMessage, LLMProvider
from app.adapters.parsers.base import ParsedMessage
from app.models.digest import Digest
from app.schemas.llm_response import DigestResponse

logger = logging.getLogger(__name__)
__all__ = ["DigestService", "FALLBACK_BLOCK"]


FALLBACK_BLOCK: dict[str, object] = {
    "topic": "错误",
    "summary": "摘要生成失败，可重试",
    "msg_range": [0, 0],
}

_SYSTEM_PROMPT = (
    "generate digest. return JSON: "
    '{"blocks":[{"topic","summary","msg_range":[start,end]}]}'
)
_WINDOW = "24h"
_DATE_FMT = "%Y-%m-%d"


class DigestService:
    """Generate and persist an LLM-produced digest for an upload."""

    def __init__(self, llm: LLMProvider, session: Session) -> None:
        self._llm = llm
        self._session = session

    def generate(self, upload_id: str, messages: Sequence) -> Digest:
        """Produce a Digest for `upload_id` from `messages`.

        Args:
            upload_id: Foreign key into uploads.id (unique per digest).
                Caller is responsible for ensuring the Upload row exists
                (FK enforcement is a DB-level concern; SQLite default off).
            messages: Sequence of ParsedMessage-like objects exposing
                `sender` and `content` attributes.

        Returns:
            The persisted Digest row (with `id` populated).
        """
        prompt = self._build_prompt(messages)
        # TODO(T17): add Upload row existence check here or rely on
        # PRAGMA foreign_keys=ON at engine creation time.
        try:
            raw = self._llm.complete(prompt, schema={"type": "json_object"})
            try:
                parsed = DigestResponse.model_validate_json(raw)
                blocks = [b.model_dump() for b in parsed.blocks]
            except (json.JSONDecodeError, ValidationError):
                logger.warning(
                    "digest fallback (bad json) for upload_id=%s", upload_id,
                    exc_info=True,
                )
                blocks = []
        except Exception:
            # LLM call raised after adapter retries exhausted — fall back.
            logger.warning(
                "digest fallback (llm error) for upload_id=%s", upload_id,
                exc_info=True,
            )
            blocks = []
        if not blocks:
            blocks = [{**FALLBACK_BLOCK}]

        digest = Digest(
            upload_id=upload_id,
            date=datetime.now(timezone.utc).strftime(_DATE_FMT),
            window=_WINDOW,
            summary_blocks=blocks,
            model_used=self._llm.name(),
        )
        self._session.add(digest)
        self._session.flush()  # populate digest.id without committing caller's txn
        return digest

    def _build_prompt(self, messages: Sequence) -> list[LLMMessage]:
        """Format messages into a system+user prompt for the LLM."""
        joined = "\n".join(
            f"{m.sender}: {m.content}" if isinstance(m, ParsedMessage) else str(m)
            for m in messages
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": joined},
        ]
