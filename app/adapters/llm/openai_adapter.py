"""OpenAI LLM adapter with retry on 5xx/network errors."""
import time

from openai import APIError, APIStatusError, OpenAI

from ..llm_provider import LLMMessage, register_provider

__all__ = ["OpenAIAdapter"]


@register_provider("openai")
class OpenAIAdapter:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        retry_max: int = 3,
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            max_retries=0,
        )
        self._model = model
        self._retry_max = retry_max

    def name(self) -> str:
        return "openai"

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
                if 400 <= e.status_code < 500:
                    raise
                last_exc = e
            except APIError as e:
                last_exc = e
            if attempt < self._retry_max - 1:
                time.sleep(2 ** attempt)
        assert last_exc is not None
        raise last_exc
