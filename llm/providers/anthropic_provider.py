"""Anthropic (Claude) provider built on the ``anthropic`` SDK.

Claude has no ``response_format=json_object`` switch, so structured output is
handled by the base class: the system prompt is nudged toward pure JSON and the
reply is parsed tolerantly (:meth:`LLMProvider._parse_structured`).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ..base import LLMProvider
from ..errors import (
    LLMAuthError,
    LLMBadResponseError,
    LLMConfigError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ..registry import register_provider
from ..types import (
    ImagePart,
    LLMResponse,
    Message,
    StreamEvent,
    TextPart,
    ToolCall,
    ToolSpec,
    Usage,
)


def _split_system(messages: list[Message]) -> tuple[str, list[Message]]:
    system_chunks: list[str] = []
    rest: list[Message] = []
    for msg in messages:
        if msg.role == "system" and isinstance(msg.content, str):
            system_chunks.append(msg.content)
        else:
            rest.append(msg)
    return "\n\n".join(system_chunks), rest


def _content_to_anthropic(content: str | list[Any]) -> Any:
    if isinstance(content, str):
        return content
    blocks: list[dict[str, Any]] = []
    for part in content:
        if isinstance(part, TextPart):
            blocks.append({"type": "text", "text": part.text})
        elif isinstance(part, ImagePart):
            url = part.url
            if url.startswith("data:"):
                header, _, b64 = url.partition(",")
                media_type = header.split(";")[0].removeprefix("data:") or "image/png"
                blocks.append(
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    }
                )
            else:
                blocks.append({"type": "image", "source": {"type": "url", "url": url}})
    return blocks


def _messages_to_anthropic(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = "assistant" if msg.role == "assistant" else "user"
        out.append({"role": role, "content": _content_to_anthropic(msg.content)})
    return out


@register_provider
class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_model = "claude-sonnet-4-20250514"
    supports_json_mode = False

    def _validate_config(self) -> None:
        if not self.api_key:
            raise LLMConfigError(
                "no API key configured for provider 'anthropic'. Set LLM_API_KEY "
                "or ANTHROPIC_API_KEY.",
                provider=self.name,
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMConfigError(
                "the 'anthropic' package is required for this provider; run "
                "`pip install anthropic`",
                provider=self.name,
            ) from exc
        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout, "max_retries": 0}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = anthropic.Anthropic(**kwargs)

    def _map_error(self, exc: Exception) -> LLMError:
        import anthropic

        if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
            return LLMAuthError(str(exc), provider=self.name)
        if isinstance(exc, anthropic.RateLimitError):
            return LLMRateLimitError(str(exc), provider=self.name)
        if isinstance(exc, anthropic.APITimeoutError):
            return LLMTimeoutError(str(exc), provider=self.name)
        if isinstance(exc, anthropic.BadRequestError):
            return LLMBadResponseError(str(exc), provider=self.name)
        if isinstance(exc, anthropic.APIConnectionError):
            return LLMProviderError(f"connection error: {exc}", provider=self.name)
        return LLMProviderError(str(exc), provider=self.name)

    def _tools_to_anthropic(self, tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools
        ]

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
        system, rest = _split_system(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens or self.default_max_tokens,
            "messages": _messages_to_anthropic(rest),
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        anthropic_tools = self._tools_to_anthropic(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        try:
            message = self._client.messages.create(**kwargs)
        except LLMError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in message.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
                )

        usage = Usage(
            prompt_tokens=getattr(message.usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(message.usage, "output_tokens", 0) or 0,
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            model=getattr(message, "model", model),
            provider=self.name,
            finish_reason=_stop_reason(getattr(message, "stop_reason", None)),
            usage=usage,
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
        system, rest = _split_system(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens or self.default_max_tokens,
            "messages": _messages_to_anthropic(rest),
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield StreamEvent(type="text", text=text)
                final = stream.get_final_message()
            usage = Usage(
                prompt_tokens=getattr(final.usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(final.usage, "output_tokens", 0) or 0,
            )
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            yield StreamEvent(type="done", usage=usage)
        except LLMError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc


def _stop_reason(value: str | None):
    mapping = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
    }
    return mapping.get(value or "", "unknown")


__all__ = ["AnthropicProvider"]
