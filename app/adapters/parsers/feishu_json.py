"""Feishu JSON chat format parser."""

import json
from datetime import datetime, timezone

from .base import ParseError, ParsedMessage


class FeishuJsonParser:
    """Parses Feishu export JSON into a list of ParsedMessage."""

    def name(self) -> str:
        return "feishu"

    def parse(self, raw: bytes) -> list[ParsedMessage]:
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

        result: list[ParsedMessage] = []
        for m in messages:
            if not isinstance(m, dict):
                raise ParseError("invalid message entry")

            try:
                ts = datetime.fromtimestamp(int(m["create_time"]), tz=timezone.utc)
            except KeyError as e:
                raise ParseError(f"missing create_time: {e}") from e
            except (TypeError, ValueError) as e:
                raise ParseError(f"bad create_time: {e}") from e

            sender_obj = m.get("sender")
            if not isinstance(sender_obj, dict):
                raise ParseError("invalid sender: expected object")
            try:
                sender = sender_obj["name"]
            except KeyError as e:
                raise ParseError(f"missing sender.name: {e}") from e

            try:
                content = m["body"]
                msg_id = m["message_id"]
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


__all__ = ["FeishuJsonParser"]
