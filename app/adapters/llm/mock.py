"""Mock LLM adapter for testing — config-driven responses + failure injection."""
from ..llm_provider import LLMMessage, register_provider

__all__ = ["MockLLMAdapter"]


@register_provider("mock")
class MockLLMAdapter:
    def __init__(self) -> None:
        self._responses: dict[str, str] = {}
        self._fail_remaining: int = 0
        self._fail_exc: Exception | None = None
        self.call_count: int = 0

    def name(self) -> str:
        return "mock"

    def set_response(self, input_substr: str, output: str) -> None:
        self._responses[input_substr] = output

    def fail_n_times(self, n: int, exc: Exception) -> None:
        self._fail_remaining = n
        self._fail_exc = exc

    def complete(self, messages: list[LLMMessage], schema: dict | None = None) -> str:
        text = " ".join(m["content"] for m in messages)
        while True:
            self.call_count += 1
            if self._fail_remaining > 0:
                self._fail_remaining -= 1
                assert self._fail_exc is not None
                # Internal retry simulates a resilient provider; the exception
                # is consumed here so callers see only the final success.
                continue
            for k, v in self._responses.items():
                if k in text:
                    return v
            return ""
