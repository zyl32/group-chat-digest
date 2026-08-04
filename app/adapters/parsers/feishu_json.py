"""Feishu JSON chat format parser."""

from datetime import datetime, timezone

from .base import ParseError, ParsedMessage, _load_message_objects


class FeishuJsonParser:
    """Parses Feishu export JSON into a list of ParsedMessage."""

    def name(self) -> str:
        return "feishu"

    def parse(self, raw: bytes) -> list[ParsedMessage]:
        messages = _load_message_objects(raw)
        result: list[ParsedMessage] = []
        for m in messages:
            ts_raw = m.get("create_time")
            try:
                ts_int = int(ts_raw)
            except (TypeError, ValueError) as e:
                raise ParseError(f"bad create_time: {e}") from e
            if ts_int < 0:
                raise ParseError(f"create_time out of range: {ts_int}")
            ts = datetime.fromtimestamp(ts_int, tz=timezone.utc)

            sender_obj = m.get("sender")
            if not isinstance(sender_obj, dict):
                raise ParseError("bad sender: expected object")
            try:
                sender = sender_obj["name"]
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
