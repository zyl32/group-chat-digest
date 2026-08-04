"""Parser protocol and shared data structures."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ParsedMessage:
    """An immutable representation of a parsed chat message."""

    sender: str
    content: str
    timestamp: datetime
    msg_id: str


class Parser(Protocol):
    """Protocol for all chat-format parsers."""

    def parse(self, raw: bytes) -> list[ParsedMessage]:
        ...

    def name(self) -> str:
        ...


class ParseError(Exception):
    """Raised when a parser fails to interpret raw bytes."""


def _load_message_objects(raw: bytes) -> list[dict]:
    """Parse raw bytes as JSON and return the 'messages' list.

    Centralizes JSON loading + structure validation shared across JSON-based
    parsers (WeChat, Feishu). Each parser then performs its own field-level
    extraction.

    Args:
        raw: Raw bytes from an uploaded chat export file.

    Returns:
        List of message dicts.

    Raises:
        ParseError: If bytes are not valid JSON, root is not an object,
            'messages' field is missing or not a list, list is empty,
            or any entry is not a dict.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ParseError("invalid payload: expected JSON object")
    messages = data.get("messages")
    if not isinstance(messages, list):
        raise ParseError("missing 'messages' field")
    if not messages:
        raise ParseError("empty messages")
    for m in messages:
        if not isinstance(m, dict):
            raise ParseError("invalid message entry")
    return messages


__all__ = ["ParsedMessage", "Parser", "ParseError", "_load_message_objects"]
