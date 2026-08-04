"""TodoExtractor: LLM-driven todo extraction with schema validation + fallback.

The service builds a prompt from parsed messages (and optional digest blocks
for topic context), calls the LLM provider, validates the JSON response
against `TodoResponse`, and persists one `Todo` row per extracted item. On
JSON/ValidationError (or LLM exception after adapter retries are exhausted)
it falls back to one "待确认" todo per message — the upload pipeline must
remain resilient to flaky LLM output. Retry logic lives in the adapter
(T11/T12), not here (YAGNI).
"""
import json
import logging
from datetime import datetime
from typing import Sequence

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.llm_provider import LLMMessage, LLMProvider
from app.adapters.parsers.base import ParsedMessage
from app.models.todo import Todo
from app.schemas.llm_response import TodoResponse

logger = logging.getLogger(__name__)
__all__ = ["TodoExtractor"]

_SYSTEM_PROMPT = (
    "extract todos. return JSON: "
    '{"todos":[{"who","what","due_at","source_msg_id"}]}'
)


def _msg_content(m: object) -> str:
    """Extract message content from dict / ParsedMessage / fallback str."""
    if isinstance(m, dict):
        return str(m.get("content", ""))
    if isinstance(m, ParsedMessage):
        return m.content
    return str(m)


class TodoExtractor:
    """Extract and persist LLM-produced todos for an upload."""

    def __init__(self, llm: LLMProvider, session: Session) -> None:
        self._llm = llm
        self._session = session

    def extract(
        self,
        upload_id: str,
        messages: Sequence,
        digest_blocks: Sequence,
    ) -> list[Todo]:
        """Produce Todo rows for `upload_id` from `messages`.

        Args:
            upload_id: Foreign key into uploads.id. Caller ensures the
                Upload row exists (FK enforcement is a DB-level concern;
                SQLite default off).
            messages: Sequence of ParsedMessage-like objects (or dicts
                with a ``content`` key) whose text is fed to the LLM.
            digest_blocks: Optional sequence of digest blocks (dicts with
                ``topic``/``summary``) providing topic context to the LLM.

        Returns:
            The persisted Todo rows (with ids populated via flush).
        """
        prompt = self._build_prompt(messages, digest_blocks)
        try:
            raw = self._llm.complete(prompt, schema={"type": "json_object"})
            try:
                parsed = TodoResponse.model_validate_json(raw)
                items = parsed.todos
            except (json.JSONDecodeError, ValidationError):
                logger.warning(
                    "todo fallback (bad json) for upload_id=%s", upload_id,
                    exc_info=True,
                )
                items = []
        except Exception:
            # LLM call raised after adapter retries exhausted — fall back.
            logger.warning(
                "todo fallback (llm error) for upload_id=%s", upload_id,
                exc_info=True,
            )
            items = []

        if not items:
            # Fallback: one "待确认" todo per message so users can triage.
            todos = [
                Todo(
                    upload_id=upload_id,
                    who=None,
                    what=f"[待确认] {_msg_content(m)[:50]}",
                    source_msg_id=i,
                    state="pending",
                )
                for i, m in enumerate(messages)
            ]
        else:
            todos = []
            for it in items:
                due = None
                if it.due_at:
                    try:
                        due = datetime.fromisoformat(it.due_at)
                    except ValueError:
                        logger.warning(
                            "bad due_at %r for upload_id=%s",
                            it.due_at, upload_id,
                        )
                todos.append(
                    Todo(
                        upload_id=upload_id,
                        who=it.who,
                        what=it.what,
                        due_at=due,
                        source_msg_id=it.source_msg_id,
                        state="pending",
                    )
                )
        for t in todos:
            self._session.add(t)
        self._session.flush()  # populate ids without committing caller's txn
        return todos

    def _build_prompt(
        self,
        messages: Sequence,
        digest_blocks: Sequence,
    ) -> list[LLMMessage]:
        """Format messages + digest topics into a system+user prompt."""
        joined = "\n".join(_msg_content(m) for m in messages)
        block_summary = ""
        if digest_blocks:
            lines = []
            for b in digest_blocks:
                if isinstance(b, dict):
                    lines.append(
                        f"- {b.get('topic', '?')}: {b.get('summary', '')}"
                    )
                else:
                    lines.append(f"- {getattr(b, 'topic', '?')}")
            block_summary = "\n\nDigest topics:\n" + "\n".join(lines)
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": joined + block_summary},
        ]
