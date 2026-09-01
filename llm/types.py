"""Provider-agnostic data types exchanged with an :class:`~llm.base.LLMProvider`.

These deliberately mirror the *concepts* an agent cares about - messages, model,
tools, streaming, structured output, token usage, errors - without leaking any
single vendor's request/response shape.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImagePart(BaseModel):
    """An image supplied as a data URL or a remote URL."""

    type: Literal["image"] = "image"
    url: str
    detail: Literal["auto", "low", "high"] = "auto"


ContentPart = TextPart | ImagePart


class Message(BaseModel):
    """A single conversation turn.

    ``content`` is either a plain string or a list of parts (for multimodal
    input). ``tool_call_id``/``name`` are only used for ``role="tool"`` results.
    """

    role: Role
    content: str | list[ContentPart] = ""
    name: str | None = None
    tool_call_id: str | None = None

    @classmethod
    def system(cls, text: str) -> Message:
        return cls(role="system", content=text)

    @classmethod
    def user(cls, content: str | list[ContentPart]) -> Message:
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, text: str) -> Message:
        return cls(role="assistant", content=text)


class ToolSpec(BaseModel):
    """A tool/function the model may call. ``parameters`` is a JSON Schema object."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    """Token accounting. Providers that do not report usage return zeros."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


FinishReason = Literal["stop", "length", "tool_calls", "content_filter", "error", "unknown"]


class LLMResponse(BaseModel):
    """The normalized result of a non-streaming completion."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model: str = ""
    provider: str = ""
    finish_reason: FinishReason = "unknown"
    usage: Usage = Field(default_factory=Usage)
    #: Raw provider payload, kept for debugging. Never relied on by callers.
    raw: dict[str, Any] | None = Field(default=None, repr=False)


StreamEventType = Literal["text", "tool_call", "usage", "done", "error"]


class StreamEvent(BaseModel):
    """One event from :meth:`~llm.base.LLMProvider.stream`."""

    type: StreamEventType
    #: Populated for ``type="text"`` - an incremental text delta.
    text: str = ""
    #: Populated for ``type="tool_call"``.
    tool_call: ToolCall | None = None
    #: Populated for ``type="usage"`` and ``type="done"`` when known.
    usage: Usage | None = None
    #: Populated for ``type="error"``.
    error: str = ""


__all__ = [
    "Role",
    "TextPart",
    "ImagePart",
    "ContentPart",
    "Message",
    "ToolSpec",
    "ToolCall",
    "Usage",
    "FinishReason",
    "LLMResponse",
    "StreamEventType",
    "StreamEvent",
]
