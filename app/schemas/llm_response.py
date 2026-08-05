"""Pydantic schemas for LLM JSON output (digest + todo).

These models are the contract between LLM adapters (which return raw JSON
strings) and the services that consume them. Services validate via
`model_validate_json`, falling back to a sentinel block on failure.
"""
from pydantic import BaseModel, ConfigDict

__all__ = ["DigestBlock", "DigestResponse", "TodoItem", "TodoResponse"]


class DigestBlock(BaseModel):
    """A single summary block produced by the digest LLM prompt."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    summary: str
    msg_range: list[int]


class DigestResponse(BaseModel):
    """Top-level LLM response for the digest prompt."""

    model_config = ConfigDict(extra="forbid")

    blocks: list[DigestBlock]


class TodoItem(BaseModel):
    """A single todo extracted from the chat.

    `source_msg_id` is the LLM-supplied index of the source message in the
    conversation (not the parser's `msg_id`, which is alphanumeric). The Todo
    model's `source_msg_id` column is `Integer` to match.
    """

    model_config = ConfigDict(extra="forbid")

    who: str | None
    what: str
    due_at: str | None
    source_msg_id: int | None


class TodoResponse(BaseModel):
    """Top-level LLM response for the todo-extraction prompt."""

    model_config = ConfigDict(extra="forbid")

    todos: list[TodoItem]
