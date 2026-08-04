"""Parser service — format selection and parsing entry point."""

from typing import Optional

from app.adapters.parsers import PARSERS, ParseError, Parser, ParsedMessage


def select_parser(fmt: str) -> Optional[Parser]:
    """Return a parser instance for ``fmt`` or ``None`` if unknown."""
    if fmt not in PARSERS:
        return None
    return PARSERS[fmt]()


def parse_upload(raw: bytes, fmt: str) -> list[ParsedMessage]:
    """Parse raw upload bytes for ``fmt``.

    Args:
        raw: Raw bytes from the uploaded chat export file.
        fmt: Parser key (e.g. ``"wechat"``, ``"feishu"``, ``"plain"``).

    Returns:
        List of :class:`ParsedMessage`.

    Raises:
        ParseError: If ``fmt`` is unknown or the parser fails to interpret
            ``raw``.
    """
    parser = select_parser(fmt)
    if parser is None:
        raise ParseError(f"unknown format: {fmt}")
    return parser.parse(raw)


__all__ = ["select_parser", "parse_upload"]
