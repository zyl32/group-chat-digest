"""Tests for DeepSeekAdapter — OpenAI-compatible SDK with retry semantics."""
import pytest
import respx
from httpx import Response
from openai import APIError

from app.adapters.llm.deepseek import DeepSeekAdapter


@respx.mock
def test_deepseek_complete_ok():
    respx.post("https://api.deepseek.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "hello back"}}]})
    )
    adapter = DeepSeekAdapter(api_key="sk-test")
    out = adapter.complete([{"role": "user", "content": "hello"}])
    assert out == "hello back"


@respx.mock
def test_deepseek_retry_on_5xx():
    route = respx.post("https://api.deepseek.com/v1/chat/completions").mock(
        return_value=Response(503)
    )
    adapter = DeepSeekAdapter(api_key="sk-test", retry_max=3)
    with pytest.raises(APIError):
        adapter.complete([{"role": "user", "content": "x"}])
    assert route.call_count == 3


@respx.mock
def test_deepseek_complete_returns_empty_on_null_content():
    """If API returns null content, complete returns empty string (not None)."""
    respx.post("https://api.deepseek.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": None}}]})
    )
    adapter = DeepSeekAdapter(api_key="sk-test")
    out = adapter.complete([{"role": "user", "content": "hello"}])
    assert out == ""


@respx.mock
def test_deepseek_4xx_no_retry():
    """4xx errors should not be retried (client error, won't recover)."""
    route = respx.post("https://api.deepseek.com/v1/chat/completions").mock(
        return_value=Response(400, json={"error": "bad request"})
    )
    adapter = DeepSeekAdapter(api_key="sk-test", retry_max=3)
    with pytest.raises(Exception):
        adapter.complete([{"role": "user", "content": "x"}])
    # 4xx should not trigger retry — only 5xx and network errors
    assert route.call_count == 1
