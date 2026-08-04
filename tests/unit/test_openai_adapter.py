"""Tests for OpenAIAdapter — OpenAI SDK with retry on 5xx/network errors."""
import pytest
import respx
from httpx import Response

from app.adapters.llm.openai_adapter import OpenAIAdapter


@respx.mock
def test_openai_complete_ok():
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "hello back"}}]})
    )
    adapter = OpenAIAdapter(api_key="sk-test")
    out = adapter.complete([{"role": "user", "content": "hello"}])
    assert out == "hello back"


@respx.mock
def test_openai_4xx_no_retry():
    """4xx errors should not be retried."""
    route = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(401, json={"error": "invalid api key"})
    )
    adapter = OpenAIAdapter(api_key="sk-test", retry_max=3)
    with pytest.raises(Exception):
        adapter.complete([{"role": "user", "content": "x"}])
    assert route.call_count == 1
