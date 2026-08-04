"""DigestService: LLM-driven chat summarization with schema + fallback.

The service builds a prompt from parsed messages, calls the LLM provider,
validates the JSON response against `DigestResponse`, and persists a
`Digest` row. On JSON/ValidationError it falls back to a sentinel block
rather than raising — the upload pipeline must remain resilient to flaky
LLM output. Retry logic lives in the adapter (T11/T12), not here (YAGNI).
"""
import json
from datetime import datetime, timezone
from typing import Sequence

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.llm_provider import LLMMessage, LLMProvider
from app.models.digest import Digest
from app.schemas.llm_response import DigestResponse

__all__ = ["DigestService", "FALLBACK_BLOCK"]


FALLBACK_BLOCK: dict = {
    "topic": "错误",
    "summary": "摘要生成失败，可重试",
    "msg_range": [0, 0],
}

_SYSTEM_PROMPT = (
    "generate digest. return JSON: "
    '{"blocks":[{"topic","summary","msg_range":[start,end]}]}'
)


class DigestService:
    """Generate and persist an LLM-produced digest for an upload."""

    def __init__(self, llm: LLMProvider, session: Session) -> None:
        self._llm = llm
        self._session = session

    def generate(self, upload_id: str, messages: Sequence) -> Digest:
        """Produce a Digest for `upload_id` from `messages`.

        Args:
            upload_id: Foreign key into uploads.id (unique per digest).
            messages: Sequence of ParsedMessage-like objects exposing
                `sender` and `content` attributes.

        Returns:
            The persisted Digest row (with `id` populated).
        """
        prompt = self._build_prompt(messages)
        raw = self._llm.complete(prompt, schema={"type": "json_object"})
        try:
            parsed = DigestResponse.model_validate_json(raw)
            blocks = [b.model_dump() for b in parsed.blocks]
        except (json.JSONDecodeError, ValidationError):
            blocks = [FALLBACK_BLOCK]
        if not blocks:
            blocks = [FALLBACK_BLOCK]

        digest = Digest(
            upload_id=upload_id,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            window="24h",
            summary_blocks=blocks,
            model_used=self._llm.name(),
        )
        self._session.add(digest)
        self._session.commit()
        self._session.refresh(digest)
        return digest

    def _build_prompt(self, messages: Sequence) -> list[LLMMessage]:
        """Format messages into a system+user prompt for the LLM."""
        joined = "\n".join(
            f"{m.sender}: {m.content}" if hasattr(m, "sender") else str(m)
            for m in messages
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": joined},
        ]
