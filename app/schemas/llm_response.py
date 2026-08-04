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

    `source_msg_id` is `str` to match `ParsedMessage.msg_id` (wechat/feishu
    IDs are alphanumeric; numeric strings would coerce under int but
    non-numeric IDs would raise).
    """

    model_config = ConfigDict(extra="forbid")

    who: str | None
    what: str
    due_at: str | None
    source_msg_id: str | None


class TodoResponse(BaseModel):
    """Top-level LLM response for the todo-extraction prompt."""

    model_config = ConfigDict(extra="forbid")

    todos: list[TodoItem]
