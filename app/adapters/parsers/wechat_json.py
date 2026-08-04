"""WeChat JSON chat format parser."""

from datetime import datetime

from .base import ParseError, ParsedMessage, _load_message_objects


class WechatJsonParser:
    """Parses WeChat export JSON into a list of ParsedMessage."""

    def name(self) -> str:
        return "wechat"

    def parse(self, raw: bytes) -> list[ParsedMessage]:
        messages = _load_message_objects(raw)
        result: list[ParsedMessage] = []
        for m in messages:
            try:
                ts = datetime.fromisoformat(m["timestamp"])
            except (KeyError, ValueError) as e:
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
