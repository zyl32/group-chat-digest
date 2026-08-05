"""Tests for DigestService: LLM-driven summary with JSON schema + fallback."""
import json
from datetime import datetime

from app.adapters.llm.mock import MockLLMAdapter
from app.adapters.parsers.base import ParsedMessage
from app.models.digest import Digest
from app.services.digest import DigestService


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


def test_digest_basic(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """Valid LLM JSON is parsed into structured blocks and persisted."""
    mock_llm.set_response(
        "generate digest",
        json.dumps(
            {
                "blocks": [
                    {"topic": "DDL", "summary": "明天交报告", "msg_range": [0, 2]}
                ]
            }
        ),
    )
    svc = DigestService(llm=mock_llm, session=in_memory_db)
    digest = svc.generate(upload_id="u1", messages=_sample_messages())

    assert len(digest.summary_blocks) == 1
    assert digest.summary_blocks[0]["topic"] == "DDL"
    assert digest.model_used == "mock"


def test_digest_fallback_on_bad_json(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """Malformed LLM output triggers the fallback block, not an exception."""
    mock_llm.set_response("generate digest", "not json")
    svc = DigestService(llm=mock_llm, session=in_memory_db)
    digest = svc.generate(upload_id="u1", messages=_sample_messages())

    assert len(digest.summary_blocks) == 1
    assert "失败" in digest.summary_blocks[0]["summary"]


def test_digest_commits_to_session(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """The Digest row is persisted in the session after generate."""
    mock_llm.set_response(
        "generate digest",
        json.dumps({"blocks": [{"topic": "X", "summary": "Y", "msg_range": [0, 1]}]}),
    )
    svc = DigestService(llm=mock_llm, session=in_memory_db)
    digest = svc.generate(upload_id="u-commit", messages=_sample_messages())

    queried = in_memory_db.query(Digest).filter_by(upload_id="u-commit").one()
    assert queried.id == digest.id
    assert queried.model_used == "mock"


def test_digest_empty_messages(in_memory_db, mock_llm: MockLLMAdapter) -> None:
    """An empty message list still yields a digest from the LLM response."""
    mock_llm.set_response(
        "generate digest",
        json.dumps({"blocks": [{"topic": "T", "summary": "S", "msg_range": [0, 0]}]}),
    )
    svc = DigestService(llm=mock_llm, session=in_memory_db)
    digest = svc.generate(upload_id="u-empty", messages=[])

    assert digest.model_used == "mock"
    assert len(digest.summary_blocks) == 1


def test_digest_fallback_on_llm_exception(in_memory_db) -> None:
    """If the LLM raises after retries are exhausted, the fallback block is used."""

    class _RaisingLLM:
        def name(self) -> str:
            return "raising-mock"

        def complete(self, messages, schema=None) -> str:
            raise RuntimeError("adapter retries exhausted")

    svc = DigestService(llm=_RaisingLLM(), session=in_memory_db)
    digest = svc.generate(upload_id="u-raise", messages=_sample_messages())

    assert len(digest.summary_blocks) == 1
    assert "失败" in digest.summary_blocks[0]["summary"]
    assert digest.model_used == "raising-mock"
