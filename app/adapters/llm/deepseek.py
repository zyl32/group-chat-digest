"""DeepSeek LLM adapter — OpenAI SDK compatible, retries on 5xx/network errors."""
from openai import OpenAI

from ._openai_base import _OpenAICompatAdapter
from ..llm_provider import register_provider

__all__ = ["DeepSeekAdapter"]


@register_provider("deepseek")
class DeepSeekAdapter(_OpenAICompatAdapter):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        retry_max: int = 3,
        base_url: str = "https://api.deepseek.com/v1",
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
        )
        self._model = model
        self._retry_max = retry_max
        self._provider_name = "deepseek"
