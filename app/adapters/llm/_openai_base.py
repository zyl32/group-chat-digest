"""Shared base for OpenAI-compatible LLM adapters (DeepSeek, OpenAI, ...).

Holds the retry loop, exception handling, and `complete()` implementation so
concrete adapters only need to configure their client and provider name.
"""
import time

from openai import APIError, APIStatusError

from ..llm_provider import LLMMessage

__all__ = ["_OpenAICompatAdapter"]


class _OpenAICompatAdapter:
    """Base class for OpenAI SDK-compatible adapters with retry on 5xx/network."""

    _client: object
    _model: str
    _retry_max: int
    _provider_name: str

    def name(self) -> str:
        return self._provider_name

    def complete(self, messages: list[LLMMessage], schema: dict | None = None) -> str:
        last_exc: Exception | None = None
        for attempt in range(self._retry_max):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"} if schema else None,
                )
                return resp.choices[0].message.content or ""
            except APIStatusError as e:
                # 4xx client errors: don't retry (won't recover)
                if 400 <= e.status_code < 500:
                    raise
                last_exc = e
            except APIError as e:
                # 5xx, network errors, etc.: retry
                last_exc = e
            if attempt < self._retry_max - 1:
                time.sleep(2 ** attempt)
        if last_exc is None:
            raise RuntimeError("retry loop exhausted without exception")
        raise last_exc
