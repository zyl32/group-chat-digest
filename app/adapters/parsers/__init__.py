"""Parsers package — chat format parsers and the parser registry."""

from .base import ParseError, Parser, ParsedMessage
from .feishu_json import FeishuJsonParser
from .wechat_json import WechatJsonParser

PARSERS: dict[str, type[Parser]] = {
    "wechat": WechatJsonParser,
    "feishu": FeishuJsonParser,
}

__all__ = [
    "Parser",
    "ParsedMessage",
    "ParseError",
    "WechatJsonParser",
    "FeishuJsonParser",
    "PARSERS",
]
