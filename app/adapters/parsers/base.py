"""Parser protocol and shared data structures."""

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


__all__ = ["ParsedMessage", "Parser", "ParseError"]
