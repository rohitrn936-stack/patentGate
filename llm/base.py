"""The provider interface every LLM backend implements.

An agent depends only on this abstract class. It knows about messages, a model
name, tools, streaming, structured output, token usage and a normalized error
hierarchy - never about a specific vendor SDK.
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import RETRYABLE_ERRORS, LLMBadResponseError, LLMError
from .types import LLMResponse, Message, StreamEvent, ToolSpec

logger = logging.getLogger("patentgate.llm")

TModel = TypeVar("TModel", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)
_CODE_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class LLMProvider(ABC):
    """Abstract base class for a chat-style LLM backend.

    Concrete providers implement :meth:`_complete` and :meth:`_stream`; retry,
    timeout budgeting and structured-output parsing live here so behaviour is
    identical across vendors.
    """

    #: Stable identifier used in configuration (``LLM_PROVIDER=<name>``).
    name: ClassVar[str] = ""
    #: Model used when neither config nor the call site specifies one.
    default_model: ClassVar[str] = ""
    #: Whether the provider natively supports a JSON-object response format.
    supports_json_mode: ClassVar[bool] = True

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_max_tokens: int = 4096,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.default_max_tokens = default_max_tokens
        self.extra = extra or {}
        self._validate_config()

    # -- lifecycle -----------------------------------------------------------

    def _validate_config(self) -> None:  # noqa: B027 - optional hook, not abstract
        """Hook for subclasses to reject missing credentials / build a client."""
        return

    # -- public API --------------------------------------------------------

    def complete(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: Sequence[ToolSpec] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Run a single non-streaming completion, with retry on transient errors."""

        return self._with_retry(
            lambda: self._complete(
                list(messages),
                model=model or self.model,
                temperature=temperature,
                max_tokens=max_tokens or self.default_max_tokens,
                tools=list(tools) if tools else None,
                response_format=response_format,
            )
        )

    def stream(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: Sequence[ToolSpec] | None = None,
    ) -> Iterator[StreamEvent]:
        """Stream a completion as incremental :class:`StreamEvent` objects.

        Streaming is not retried once bytes have been yielded.
        """

        yield from self._stream(
            list(messages),
            model=model or self.model,
            temperature=temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            tools=list(tools) if tools else None,
        )

    def complete_structured(
        self,
        messages: Sequence[Message],
        schema: type[TModel],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        repair: bool = True,
    ) -> TModel:
        """Return a validated ``schema`` instance from the model's JSON output.

        Uses the provider's native JSON mode when available and always falls
        back to tolerant extraction (code-fence stripping, first JSON block).
        On a validation failure a single repair round-trip is attempted.
        """

        msgs = list(messages)
        response_format = {"type": "json_object"} if self.supports_json_mode else None
        if not self.supports_json_mode:
            msgs = self._nudge_json(msgs)

        response = self.complete(
            msgs,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        try:
            return self._parse_structured(response.text, schema)
        except LLMBadResponseError:
            if not repair:
                raise
            logger.warning("structured output failed for %s; attempting one repair", schema.__name__)

        repair_msgs = msgs + [
            Message.assistant(response.text or ""),
            Message.user(
                "That response could not be parsed as valid JSON for the required "
                "schema. Reply again with ONLY the corrected JSON object, no prose, "
                "no code fences."
            ),
        ]
        repaired = self.complete(
            repair_msgs,
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return self._parse_structured(repaired.text, schema)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _nudge_json(messages: list[Message]) -> list[Message]:
        instruction = (
            "You must respond with a single valid JSON value and nothing else. "
            "Do not wrap it in markdown code fences."
        )
        out = list(messages)
        if out and out[0].role == "system" and isinstance(out[0].content, str):
            out[0] = Message.system(f"{out[0].content}\n\n{instruction}")
        else:
            out.insert(0, Message.system(instruction))
        return out

    @staticmethod
    def _parse_structured(text: str, schema: type[TModel]) -> TModel:
        cleaned = _CODE_FENCE.sub("", (text or "").strip())
        candidates = [cleaned]
        match = _JSON_BLOCK.search(cleaned)
        if match:
            candidates.append(match.group(0))

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            try:
                return schema.model_validate(data)
            except ValidationError as exc:
                last_error = exc
        raise LLMBadResponseError(
            f"could not parse a valid {schema.__name__} from the model response: {last_error}"
        )

    def _with_retry(self, call):
        deadline = time.monotonic() + self.timeout * (self.max_retries + 1)
        attempt = 0
        while True:
            try:
                return call()
            except LLMError as exc:
                attempt += 1
                retryable = isinstance(exc, RETRYABLE_ERRORS)
                if not retryable or attempt > self.max_retries or time.monotonic() >= deadline:
                    raise
                backoff = min(2.0 ** (attempt - 1), 8.0)
                logger.warning(
                    "llm call failed (%s), retry %d/%d in %.1fs",
                    exc.code,
                    attempt,
                    self.max_retries,
                    backoff,
                )
                time.sleep(backoff)

    # -- provider contract ---------------------------------------------

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def _stream(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float | None,
        max_tokens: int,
        tools: list[ToolSpec] | None,
    ) -> Iterator[StreamEvent]:
        raise NotImplementedError


__all__ = ["LLMProvider"]
