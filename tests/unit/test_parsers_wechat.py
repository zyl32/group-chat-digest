from pathlib import Path
import pytest
from app.adapters.parsers.wechat_json import WechatJsonParser
from app.adapters.parsers.base import ParseError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_wechat_normal():
    raw = (FIXTURES / "wechat_sample.json").read_bytes()
    parser = WechatJsonParser()
    msgs = parser.parse(raw)
    assert len(msgs) == 2
    assert msgs[0].sender == "张三"
    assert msgs[0].content == "明天交报告"
    assert msgs[1].msg_id == "m2"


def test_wechat_empty():
    parser = WechatJsonParser()
    with pytest.raises(ParseError, match="empty"):
        parser.parse(b'{"messages": []}')


def test_wechat_malformed():
    parser = WechatJsonParser()
    with pytest.raises(ParseError):
        parser.parse(b'not json at all')
