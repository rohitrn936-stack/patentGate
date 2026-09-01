"""Test helpers: a scripted in-memory provider with no network access.

Usage::

    from llm.testing import FakeProvider, use_fake_llm

    with use_fake_llm(responses=['{"answer": 42}']):
        result = get_llm(agent="agent1").complete_structured(msgs, Schema)
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .base import LLMProvider
from .errors import LLMError
from .registry import register_provider, reset_provider_cache
from .types import LLMResponse, Message, StreamEvent, ToolCall, ToolSpec, Usage


@register_provider
class FakeProvider(LLMProvider):
    """Returns pre-scripted responses in order; records calls for assertions."""

    name = "fake"
    default_model = "fake-1"
    supports_json_mode = True

    # Class-level script shared by every instance (providers are cached).
    responses: list[str | LLMError] = []
    tool_calls: list[list[ToolCall]] = []
    calls: list[dict[str, Any]] = []
    _cursor = 0

    @classmethod
    def script(
        cls,
        responses: list[str | LLMError] | None = None,
        tool_calls: list[list[ToolCall]] | None = None,
    ) -> None:
        cls.responses = list(responses or [])
        cls.tool_calls = list(tool_calls or [])
        cls.calls = []
        cls._cursor = 0
        reset_provider_cache()

    def _validate_config(self) -> None:  # no credentials required
        return

    def _next(self) -> str | LLMError:
        cls = type(self)
        if cls._cursor < len(cls.responses):
            item = cls.responses[cls._cursor]
        elif cls.responses:
            item = cls.responses[-1]
        else:
            item = '{"ok": true}'
        cls._cursor += 1
        return item

    def _complete(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float | None,
        max_tokens: int,
        tools: list[ToolSpec] | None,
        response_format: dict[str, Any] | None,
    ) -> LLMResponse:
        cls = type(self)
        idx = cls._cursor
        cls.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tools": tools,
                "response_format": response_format,
            }
        )
        item = self._next()
        if isinstance(item, LLMError):
            raise item
        calls = cls.tool_calls[idx] if idx < len(cls.tool_calls) else []
        return LLMResponse(
            text=item,
            tool_calls=calls,
            model=model,
            provider=self.name,
            finish_reason="tool_calls" if calls else "stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    def _stream(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float | None,
        max_tokens: int,
        tools: list[ToolSpec] | None,
    ) -> Iterator[StreamEvent]:
        item = self._next()
        if isinstance(item, LLMError):
            raise item
        for chunk in _chunks(item, 16):
            yield StreamEvent(type="text", text=chunk)
        yield StreamEvent(type="done", usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15))


def _chunks(text: str, size: int) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


@contextmanager
def use_fake_llm(
    responses: list[str | LLMError] | None = None,
    tool_calls: list[list[ToolCall]] | None = None,
):
    """Context manager that points ``LLM_PROVIDER`` at :class:`FakeProvider`."""

    import os

    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "fake"
    FakeProvider.script(responses, tool_calls)
    try:
        yield FakeProvider
    finally:
        if previous is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous
        reset_provider_cache()


__all__ = ["FakeProvider", "use_fake_llm"]
