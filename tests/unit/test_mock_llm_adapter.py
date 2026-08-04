import pytest
from app.adapters.llm.mock import MockLLMAdapter
from app.adapters.llm_provider import LLMProvider, get_provider, LLM_PROVIDERS


def test_returns_configured_response():
    llm = MockLLMAdapter()
    llm.set_response("hello", "world")
    out = llm.complete([{"role": "user", "content": "hello"}])
    assert out == "world"


def test_call_count():
    llm = MockLLMAdapter()
    llm.set_response("a", "1")
    llm.complete([{"role": "user", "content": "a"}])
    llm.complete([{"role": "user", "content": "a"}])
    assert llm.call_count == 2


def test_failure_injection():
    llm = MockLLMAdapter()
    llm.fail_n_times(2, RuntimeError("net"))
    llm.set_response("x", "y")
    assert llm.complete([{"role": "user", "content": "x"}]) == "y"
    assert llm.call_count == 3  # 2 failed + 1 success


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown LLM provider"):
        get_provider("bogus")


def test_mock_registered_in_registry():
    assert "mock" in LLM_PROVIDERS
    provider = get_provider("mock")
    assert isinstance(provider, MockLLMAdapter)


def test_mock_satisfies_llmprovider_protocol():
    """Structural typing: MockLLMAdapter has complete() and name() matching LLMProvider."""
    llm = MockLLMAdapter()
    assert isinstance(llm, LLMProvider)  # runtime_checkable Protocol
