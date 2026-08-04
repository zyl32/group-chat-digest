"""WeChat JSON chat format parser."""

import json
from datetime import datetime

from .base import ParseError, ParsedMessage


class WechatJsonParser:
    """Parses WeChat export JSON into a list of ParsedMessage."""

    def name(self) -> str:
        return "wechat"

    def parse(self, raw: bytes) -> list[ParsedMessage]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ParseError(f"invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ParseError("root must be a JSON object")

        messages = data.get("messages")
        if not isinstance(messages, list):
            raise ParseError("missing 'messages' field")

        if not messages:
            raise ParseError("empty messages")

        result: list[ParsedMessage] = []
        for m in messages:
            if not isinstance(m, dict):
                raise ParseError("each message must be a JSON object")
            try:
                ts = datetime.fromisoformat(m["timestamp"])
            except KeyError as e:
                raise ParseError(f"missing timestamp: {e}") from e
            except ValueError as e:
                raise ParseError(f"bad timestamp: {e}") from e

            try:
                sender = m["sender"]
                content = m["content"]
                msg_id = m["msg_id"]
            except KeyError as e:
                raise ParseError(f"missing field: {e}") from e

            result.append(
                ParsedMessage(
                    sender=sender,
                    content=content,
                    timestamp=ts,
                    msg_id=msg_id,
                )
            )
        return result


__all__ = ["WechatJsonParser"]
