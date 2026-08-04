"""Parsers package — chat format parsers and the parser registry."""

from .base import ParseError, Parser, ParsedMessage
from .feishu_json import FeishuJsonParser
from .plain_text import PlainTextParser
from .wechat_json import WechatJsonParser

PARSERS: dict[str, type[Parser]] = {
    "wechat": WechatJsonParser,
    "feishu": FeishuJsonParser,
    "plain": PlainTextParser,
}

__all__ = [
    "Parser",
    "ParsedMessage",
    "ParseError",
    "WechatJsonParser",
    "FeishuJsonParser",
    "PlainTextParser",
    "PARSERS",
]
