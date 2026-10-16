"""OpenAI (and OpenAI-compatible) provider built on the ``openai`` SDK.

This one class also backs every OpenAI-wire-compatible endpoint - OpenRouter,
Google's Gemini compatibility layer, and local servers such as Ollama, vLLM or
LM Studio - via thin ``base_url`` subclasses in :mod:`llm.providers.compatible`.
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


def _content_to_openai(content: str | list[Any]) -> Any:
    if isinstance(content, str):
        return content
    parts: list[dict[str, Any]] = []
    for part in content:
        if isinstance(part, TextPart):
            parts.append({"type": "text", "text": part.text})
        elif isinstance(part, ImagePart):
            parts.append(
                {"type": "image_url", "image_url": {"url": part.url, "detail": part.detail}}
            )
    return parts


def _messages_to_openai(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        entry: dict[str, Any] = {"role": msg.role, "content": _content_to_openai(msg.content)}
        if msg.name:
            entry["name"] = msg.name
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        out.append(entry)
    return out


def _tools_to_openai(tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


@register_provider
class OpenAIProvider(LLMProvider):
    name = "openai"
    default_model = "gpt-4o-mini"
    supports_json_mode = True

    #: Overridden by compatible subclasses (OpenRouter, Gemini, local).
    _default_base_url: str | None = None
    _requires_api_key: bool = True

    def _validate_config(self) -> None:
        if self.base_url is None:
            self.base_url = self._default_base_url
        if self._requires_api_key and not self.api_key:
            raise LLMConfigError(
                f"no API key configured for provider '{self.name}'. Set LLM_API_KEY "
                f"(or the legacy provider-specific variable).",
                provider=self.name,
            )
        self._client = self._make_client()

    def _make_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMConfigError(
                "the 'openai' package is required for this provider; run "
                "`pip install openai`",
                provider=self.name,
            ) from exc

        kwargs: dict[str, Any] = {
            "api_key": self.api_key or "not-needed",
            "timeout": self.timeout,
            # Retry/backoff is handled by LLMProvider._with_retry.
            "max_retries": 0,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    # -- error mapping ---------------------------------------------------

    def _map_error(self, exc: Exception) -> LLMError:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            PermissionDeniedError,
            RateLimitError,
        )

        if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
            return LLMAuthError(str(exc), provider=self.name)
        if isinstance(exc, RateLimitError):
            return LLMRateLimitError(str(exc), provider=self.name)
        if isinstance(exc, APITimeoutError):
            return LLMTimeoutError(str(exc), provider=self.name)
        if isinstance(exc, BadRequestError):
            return LLMBadResponseError(str(exc), provider=self.name)
        if isinstance(exc, APIConnectionError):
            return LLMProviderError(f"connection error: {exc}", provider=self.name)
        return LLMProviderError(str(exc), provider=self.name)

    # -- provider contract --------------------------------------------

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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _messages_to_openai(messages),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        openai_tools = _tools_to_openai(tools)
        if openai_tools:
            kwargs["tools"] = openai_tools
        if response_format and self.supports_json_mode:
            kwargs["response_format"] = response_format
        kwargs.update(self.extra.get("completion_kwargs", {}))

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except LLMError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc

        choice = completion.choices[0] if completion.choices else None
        if choice is None:
            raise LLMBadResponseError("provider returned no choices", provider=self.name)

        message = choice.message
        tool_calls: list[ToolCall] = []
        for call in getattr(message, "tool_calls", None) or []:
            fn = getattr(call, "function", None)
            if fn is None:
                continue
            import json as _json

            try:
                args = _json.loads(fn.arguments or "{}")
            except _json.JSONDecodeError:
                args = {"_raw": fn.arguments}
            tool_calls.append(ToolCall(id=call.id, name=fn.name, arguments=args))

        usage = Usage()
        if completion.usage:
            usage = Usage(
                prompt_tokens=completion.usage.prompt_tokens or 0,
                completion_tokens=completion.usage.completion_tokens or 0,
                total_tokens=completion.usage.total_tokens or 0,
            )

        return LLMResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            model=getattr(completion, "model", model),
            provider=self.name,
            finish_reason=_finish_reason(getattr(choice, "finish_reason", None)),
            usage=usage,
            raw=None,
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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _messages_to_openai(messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        openai_tools = _tools_to_openai(tools)
        if openai_tools:
            kwargs["tools"] = openai_tools

        try:
            stream = self._client.chat.completions.create(**kwargs)
            final_usage: Usage | None = None
            for chunk in stream:
                if getattr(chunk, "usage", None):
                    final_usage = Usage(
                        prompt_tokens=chunk.usage.prompt_tokens or 0,
                        completion_tokens=chunk.usage.completion_tokens or 0,
                        total_tokens=chunk.usage.total_tokens or 0,
                    )
                for choice in getattr(chunk, "choices", None) or []:
                    delta = getattr(choice, "delta", None)
                    if delta is not None and getattr(delta, "content", None):
                        yield StreamEvent(type="text", text=delta.content)
            yield StreamEvent(type="done", usage=final_usage)
        except LLMError:
            raise
        except Exception as exc:
            raise self._map_error(exc) from exc


def _finish_reason(value: str | None):
    mapping = {
        "stop": "stop",
        "length": "length",
        "tool_calls": "tool_calls",
        "function_call": "tool_calls",
        "content_filter": "content_filter",
    }
    return mapping.get(value or "", "unknown")


__all__ = ["OpenAIProvider"]
