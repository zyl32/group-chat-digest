"""Parsers package — chat format parsers and the parser registry."""

from .base import ParseError, Parser, ParsedMessage
from .wechat_json import WechatJsonParser

PARSERS: dict[str, type[Parser]] = {"wechat": WechatJsonParser}

__all__ = ["Parser", "ParsedMessage", "ParseError", "WechatJsonParser", "PARSERS"]
