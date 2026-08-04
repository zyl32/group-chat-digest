from pathlib import Path

from app.adapters.parsers.wechat_json import WechatJsonParser
from app.adapters.parsers.base import ParseError


def test_wechat_normal():
    raw = Path("tests/fixtures/wechat_sample.json").read_bytes()
    parser = WechatJsonParser()
    msgs = parser.parse(raw)
    assert len(msgs) == 2
    assert msgs[0].sender == "张三"
    assert msgs[0].content == "明天交报告"
    assert msgs[1].msg_id == "m2"


def test_wechat_empty():
    parser = WechatJsonParser()
    try:
        parser.parse(b'{"messages": []}')
    except ParseError as e:
        assert "empty" in str(e).lower()
    else:
        assert False, "expected ParseError"


def test_wechat_malformed():
    parser = WechatJsonParser()
    try:
        parser.parse(b'not json at all')
    except ParseError:
        pass
    else:
        assert False, "expected ParseError"
