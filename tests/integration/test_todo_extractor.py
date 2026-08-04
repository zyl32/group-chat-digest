"""Tests for TodoExtractor: LLM-driven todo extraction with fallback."""
import json
from datetime import datetime

from app.adapters.llm.mock import MockLLMAdapter
from app.adapters.parsers.base import ParsedMessage
from app.models.todo import Todo
from app.services.todo import TodoExtractor


def _sample_messages() -> list[ParsedMessage]:
    """Return two fixed ParsedMessage instances for deterministic tests."""
    return [
        ParsedMessage(
            sender="张三",
            content="明天交报告",
            timestamp=datetime(2026, 8, 5, 10, 0, 0),
            msg_id="m1",
        ),
        ParsedMessage(
            sender="李四",
            content="收到",
            timestamp=datetime(2026, 8, 5, 10, 0, 5),
            msg_id="m2",
        ),
    ]


def test_extract_basic(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """Valid LLM JSON is parsed into Todo rows with state=pending."""
    mock_llm.set_response("extract", json.dumps({
        "todos": [
            {"who": "张三", "what": "交报告", "due_at": "2026-08-10", "source_msg_id": 0}
        ]
    }))
    svc = TodoExtractor(llm=mock_llm, session=in_memory_db)
    todos = svc.extract(upload_id="u1", messages=_sample_messages(), digest_blocks=[])

    assert len(todos) == 1
    assert todos[0].who == "张三"
    assert todos[0].what == "交报告"
    assert todos[0].state == "pending"
    assert todos[0].source_msg_id == 0
    assert todos[0].due_at == datetime(2026, 8, 10)


def test_extract_fallback_to_pending(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """Malformed LLM output triggers one '待确认' todo per message."""
    mock_llm.set_response("extract", "not json")
    svc = TodoExtractor(llm=mock_llm, session=in_memory_db)
    msgs = _sample_messages()
    todos = svc.extract(upload_id="u1", messages=msgs, digest_blocks=[])

    assert len(todos) == len(msgs)
    for i, t in enumerate(todos):
        assert "待确认" in t.what
        assert t.state == "pending"
        assert t.source_msg_id == i
        assert t.who is None


def test_extract_fallback_on_llm_exception(in_memory_db) -> None:
    """If the LLM raises after retries are exhausted, fallback todos are produced."""

    class _RaisingLLM:
        def name(self) -> str:
            return "raising-mock"

        def complete(self, messages, schema=None) -> str:
            raise RuntimeError("adapter retries exhausted")

    svc = TodoExtractor(llm=_RaisingLLM(), session=in_memory_db)
    msgs = _sample_messages()
    todos = svc.extract(upload_id="u-raise", messages=msgs, digest_blocks=[])

    assert len(todos) == len(msgs)
    assert all("待确认" in t.what for t in todos)
    assert all(t.state == "pending" for t in todos)


def test_extract_bad_due_at_falls_back_to_none(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """A malformed due_at string is logged and stored as NULL, not raised."""
    mock_llm.set_response("extract", json.dumps({
        "todos": [
            {"who": "张三", "what": "交报告", "due_at": "not-a-date", "source_msg_id": 0}
        ]
    }))
    svc = TodoExtractor(llm=mock_llm, session=in_memory_db)
    todos = svc.extract(upload_id="u1", messages=_sample_messages(), digest_blocks=[])

    assert len(todos) == 1
    assert todos[0].due_at is None
    assert todos[0].what == "交报告"


def test_extract_persists_to_session(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """Todos are flushed to the session so callers see ids before commit."""
    mock_llm.set_response("extract", json.dumps({
        "todos": [
            {"who": "张三", "what": "交报告", "due_at": None, "source_msg_id": 0}
        ]
    }))
    svc = TodoExtractor(llm=mock_llm, session=in_memory_db)
    todos = svc.extract(upload_id="u-persist", messages=_sample_messages(), digest_blocks=[])

    queried = in_memory_db.query(Todo).filter_by(upload_id="u-persist").all()
    assert len(queried) == 1
    assert queried[0].id == todos[0].id
