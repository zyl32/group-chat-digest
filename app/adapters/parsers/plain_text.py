"""Plain-text chat parser.

Parses line-based chat exports of the form:
    [YYYY-MM-DD HH:MM:SS] Sender: content
"""

import re
from datetime import datetime

from .base import ParseError, ParsedMessage, Parser

_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] ([^:]+): (.*)$")

__all__ = ["PlainTextParser"]


class PlainTextParser:
    """Parser for plain-text chat exports (one message per line)."""

    def name(self) -> str:
        return "plain"

    def parse(self, raw: bytes) -> list[ParsedMessage]:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ParseError(f"non-utf8 input: {e}") from e

        result: list[ParsedMessage] = []
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            m = _LINE_RE.match(stripped)
            if not m:
                raise ParseError(f"line {i}: bad format")
            try:
                ts = datetime.fromisoformat(m.group(1))
            except ValueError as e:
                raise ParseError(f"line {i}: bad timestamp: {e}") from e
            result.append(
                ParsedMessage(
                    sender=m.group(2).strip(),
                    content=m.group(3),
                    timestamp=ts,
                    msg_id=f"plain-{i}",
                )
            )
        if not result:
            raise ParseError("empty input")
        return result
