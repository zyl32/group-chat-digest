"""OpenAI LLM adapter with retry on 5xx/network errors."""
from openai import OpenAI

from ._openai_base import _OpenAICompatAdapter
from ..llm_provider import register_provider

__all__ = ["OpenAIAdapter"]


@register_provider("openai")
class OpenAIAdapter(_OpenAICompatAdapter):
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
        self._provider_name = "openai"
