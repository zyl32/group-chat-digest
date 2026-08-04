"""Pydantic schemas for LLM JSON output (digest + todo).

These models are the contract between LLM adapters (which return raw JSON
strings) and the services that consume them. Services validate via
`model_validate_json`, falling back to a sentinel block on failure.
"""
from pydantic import BaseModel

__all__ = ["DigestBlock", "DigestResponse", "TodoItem", "TodoResponse"]


class DigestBlock(BaseModel):
    """A single summary block produced by the digest LLM prompt."""

    topic: str
    summary: str
    msg_range: list[int]


class DigestResponse(BaseModel):
    """Top-level LLM response for the digest prompt."""

    blocks: list[DigestBlock]


class TodoItem(BaseModel):
    """A single todo extracted from the chat."""

    who: str | None
    what: str
    due_at: str | None
    source_msg_id: int | None


class TodoResponse(BaseModel):
    """Top-level LLM response for the todo-extraction prompt."""

    todos: list[TodoItem]
