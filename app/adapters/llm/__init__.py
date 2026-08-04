"""LLM adapter implementations."""
from .mock import MockLLMAdapter
from ..llm_provider import register_provider  # noqa: F401 — triggers registry import

__all__ = ["MockLLMAdapter"]
