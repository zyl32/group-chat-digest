from pathlib import Path

import pytest

from app.adapters.parsers.base import ParseError
from app.adapters.parsers.plain_text import PlainTextParser

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_plain_normal():
    raw = (FIXTURES / "plain_sample.txt").read_bytes()
    msgs = PlainTextParser().parse(raw)
    assert len(msgs) == 2
    assert msgs[0].sender == "张三"
    assert msgs[0].content == "明天交报告"
    assert msgs[1].sender == "李四"
    assert msgs[1].msg_id == "plain-2"


def test_plain_empty():
    parser = PlainTextParser()
    with pytest.raises(ParseError, match="empty"):
        parser.parse(b"")


def test_plain_malformed_line():
    parser = PlainTextParser()
    with pytest.raises(ParseError, match="bad format"):
        parser.parse(b"this is not a valid line\n")


def test_plain_non_utf8():
    parser = PlainTextParser()
    with pytest.raises(ParseError, match="utf"):
        parser.parse(b"\xff\xfe\x00")  # invalid UTF-8


def test_plain_skips_blank_lines():
    parser = PlainTextParser()
    raw = "[2026-08-05 10:00:00] 张三: hi\n\n   \n[2026-08-05 10:01:00] 李四: yo".encode("utf-8")
    msgs = parser.parse(raw)
    assert len(msgs) == 2
    assert msgs[0].sender == "张三"
    assert msgs[1].sender == "李四"
