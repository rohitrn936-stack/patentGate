"""Provider-agnostic LLM layer for PatentGate.

Agents depend on this package, never on a vendor SDK::

    from llm import get_llm, Message

    llm = get_llm(agent="agent1")          # provider chosen by env config
    result = llm.complete_structured(
        [Message.system(SYSTEM_PROMPT), Message.user(user_text)],
        MySchema,
    )
    print(result, llm.model, result.usage if hasattr(result, "usage") else None)

Configuration (see :mod:`llm.config`)::

    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-sonnet-4-6
    LLM_API_KEY=...
    # optional per-agent override:
    AGENT1_LLM_PROVIDER=openai
    AGENT1_LLM_MODEL=gpt-4o-mini
"""

from __future__ import annotations

from .base import LLMProvider
from .config import LLMConfig, resolve_llm_config
from .errors import (
    LLMAuthError,
    LLMBadResponseError,
    LLMConfigError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .registry import (
    available_providers,
    build_provider,
    get_llm,
    get_provider_class,
    register_provider,
    reset_provider_cache,
)
from .types import (
    ContentPart,
    ImagePart,
    LLMResponse,
    Message,
    StreamEvent,
    TextPart,
    ToolCall,
    ToolSpec,
    Usage,
)

__all__ = [
    # factory / registry
    "get_llm",
    "build_provider",
    "get_provider_class",
    "register_provider",
    "available_providers",
    "reset_provider_cache",
    # config
    "LLMConfig",
    "resolve_llm_config",
    # base
    "LLMProvider",
    # types
    "Message",
    "TextPart",
    "ImagePart",
    "ContentPart",
    "ToolSpec",
    "ToolCall",
    "Usage",
    "LLMResponse",
    "StreamEvent",
    # errors
    "LLMError",
    "LLMConfigError",
    "LLMAuthError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMBadResponseError",
    "LLMProviderError",
]
