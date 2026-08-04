"""LLMProvider protocol, Registry, and factory for Group Chat Digest.

Implements the Factory/Registry pattern per coding-style.md:
- `LLM_PROVIDERS` is the central registry (runtime-immutable via MappingProxyType)
- `register_provider(name)` is the class decorator for adapters
- `get_provider(name, **kwargs)` is the factory entrypoint

LLMMessage is a TypedDict giving static type-checking on message shape; since
the OpenAI SDK accepts plain dicts, callers can pass LLMMessage-shaped dicts
interchangeably.
"""
from types import MappingProxyType
from typing import Final, Mapping, Protocol, TypedDict, runtime_checkable

__all__ = ["LLMMessage", "LLMProvider", "LLM_PROVIDERS", "register_provider", "get_provider"]


class LLMMessage(TypedDict):
    role: str
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, messages: list[LLMMessage], schema: dict | None = None) -> str: ...
    def name(self) -> str: ...


_LLM_PROVIDERS: dict[str, type[LLMProvider]] = {}
LLM_PROVIDERS: Final[Mapping[str, type[LLMProvider]]] = MappingProxyType(_LLM_PROVIDERS)


def register_provider(name: str):
    """Class decorator: register an LLMProvider implementor under `name`."""

    def decorator(cls: type[LLMProvider]) -> type[LLMProvider]:
        _LLM_PROVIDERS[name] = cls
        return cls

    return decorator


def get_provider(name: str, **kwargs) -> LLMProvider:
    if name not in _LLM_PROVIDERS:
        raise ValueError(f"unknown LLM provider: {name}")
    return _LLM_PROVIDERS[name](**kwargs)
