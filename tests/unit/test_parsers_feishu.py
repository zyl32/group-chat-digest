from pathlib import Path
import pytest
from app.adapters.parsers.feishu_json import FeishuJsonParser
from app.adapters.parsers.base import ParseError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_feishu_normal():
    raw = (FIXTURES / "feishu_sample.json").read_bytes()
    parser = FeishuJsonParser()
    msgs = parser.parse(raw)
    assert len(msgs) == 1
    assert msgs[0].sender == "王五"
    assert msgs[0].content == "今天开会"
    assert msgs[0].msg_id == "fm1"


def test_feishu_empty():
    parser = FeishuJsonParser()
    with pytest.raises(ParseError, match="empty"):
        parser.parse(b'{"messages": []}')


def test_feishu_malformed():
    parser = FeishuJsonParser()
    with pytest.raises(ParseError):
        parser.parse(b'not json')


def test_feishu_missing_sender():
    parser = FeishuJsonParser()
    with pytest.raises(ParseError, match="sender"):
        parser.parse(b'{"messages": [{"body": "x", "create_time": "1735431600", "message_id": "m1"}]}')


def test_feishu_missing_create_time():
    parser = FeishuJsonParser()
    with pytest.raises(ParseError, match="create_time"):
        parser.parse(b'{"messages": [{"sender": {"name": "x"}, "body": "y", "message_id": "m1"}]}')


def test_feishu_negative_create_time():
    parser = FeishuJsonParser()
    with pytest.raises(ParseError, match="out of range"):
        parser.parse(b'{"messages": [{"sender": {"name": "x"}, "body": "y", "create_time": "-1", "message_id": "m1"}]}')
