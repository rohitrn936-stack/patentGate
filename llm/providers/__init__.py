"""Built-in providers. Importing this module registers all of them.

To add a provider, create a module here, implement
:class:`~llm.base.LLMProvider`, decorate the class with
``@register_provider``, and import it below.
"""

from __future__ import annotations

from .anthropic_provider import AnthropicProvider
from .compatible import GeminiProvider, LocalProvider, OpenRouterProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "OpenRouterProvider",
    "GeminiProvider",
    "LocalProvider",
]
