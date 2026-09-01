"""OpenAI-wire-compatible providers that differ only by base URL / defaults.

Each is a real, separately-selectable provider (``LLM_PROVIDER=openrouter`` etc.)
but shares all request/response handling with :class:`OpenAIProvider`.
"""

from __future__ import annotations

from ..registry import register_provider
from .openai_provider import OpenAIProvider


@register_provider
class OpenRouterProvider(OpenAIProvider):
    """https://openrouter.ai - one key, hundreds of models from many vendors."""

    name = "openrouter"
    default_model = "openai/gpt-4o-mini"
    _default_base_url = "https://openrouter.ai/api/v1"


@register_provider
class GeminiProvider(OpenAIProvider):
    """Google Gemini via its OpenAI-compatible endpoint (no extra SDK needed)."""

    name = "gemini"
    default_model = "gemini-2.0-flash"
    _default_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"


@register_provider
class LocalProvider(OpenAIProvider):
    """A self-hosted OpenAI-compatible server: Ollama, vLLM, LM Studio, llama.cpp.

    An API key is optional; ``LLM_BASE_URL`` defaults to Ollama's local port.
    """

    name = "local"
    default_model = "llama3.1"
    _default_base_url = "http://localhost:11434/v1"
    _requires_api_key = False


__all__ = ["OpenRouterProvider", "GeminiProvider", "LocalProvider"]
