"""Normalized error hierarchy for the LLM provider layer.

Every provider maps its SDK-specific exceptions onto these types so that callers
(agents, the backend, tests) never have to import ``openai`` or ``anthropic`` to
handle failures.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for every error raised by the ``llm`` package."""

    #: Coarse machine-readable code, useful for API responses and logging.
    code: str = "llm_error"

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = super().__str__()
        return f"[{self.provider}] {base}" if self.provider else base


class LLMConfigError(LLMError):
    """Raised when provider configuration is missing or invalid.

    Example: no API key, unknown provider name, unsupported model string.
    """

    code = "llm_config_error"


class LLMAuthError(LLMError):
    """The provider rejected the credentials (401/403)."""

    code = "llm_auth_error"


class LLMRateLimitError(LLMError):
    """The provider is rate limiting or over quota (429)."""

    code = "llm_rate_limit"


class LLMTimeoutError(LLMError):
    """The request exceeded the configured timeout or the provider timed out."""

    code = "llm_timeout"


class LLMBadResponseError(LLMError):
    """The provider replied, but the payload could not be used.

    Example: empty completion, invalid JSON when structured output was
    requested, or a response that failed schema validation.
    """

    code = "llm_bad_response"


class LLMProviderError(LLMError):
    """Any other upstream provider failure (5xx, network, unexpected SDK error)."""

    code = "llm_provider_error"


#: Errors that are worth retrying with backoff.
RETRYABLE_ERRORS: tuple[type[LLMError], ...] = (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMProviderError,
)


__all__ = [
    "LLMError",
    "LLMConfigError",
    "LLMAuthError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMBadResponseError",
    "LLMProviderError",
    "RETRYABLE_ERRORS",
]
