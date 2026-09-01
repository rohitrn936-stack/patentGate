"""Centralized, environment-driven LLM configuration.

Precedence for every setting (first non-empty wins):

1. Per-agent override:      ``<AGENT>_LLM_PROVIDER``, ``<AGENT>_LLM_MODEL`` ...
2. Global:                  ``LLM_PROVIDER``, ``LLM_MODEL``, ``LLM_API_KEY`` ...
3. Legacy fallback:         ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` / ``API_KEY``,
                            ``OPENAI_MODEL`` / ``MODEL_NAME``
4. Built-in default:        provider ``openai``, per-provider default model

``<AGENT>`` is the upper-cased agent key passed to :func:`resolve_llm_config`
(e.g. ``agent1`` -> ``AGENT1_LLM_MODEL``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .errors import LLMConfigError

_TRUE = {"1", "true", "yes", "on"}

# Provider name -> env var that legacy deployments used for its key.
_LEGACY_KEY_ENV: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY", "API_KEY"),
    "anthropic": ("ANTHROPIC_API_KEY", "API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "API_KEY"),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "API_KEY"),
    "local": ("LOCAL_LLM_API_KEY",),
}
_LEGACY_MODEL_ENV = ("OPENAI_MODEL", "MODEL_NAME")


@dataclass(frozen=True)
class LLMConfig:
    """A fully-resolved configuration ready to instantiate a provider."""

    provider: str
    model: str | None
    api_key: str | None
    base_url: str | None
    timeout_seconds: float
    max_retries: int
    max_tokens: int
    agent: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _first_env(*names: str) -> str | None:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return None


def _agent_prefix(agent: str | None) -> list[str]:
    if not agent:
        return []
    normalized = agent.strip().upper().replace("-", "_")
    return [normalized]


def _lookup(key: str, agent: str | None) -> str | None:
    names: list[str] = []
    for prefix in _agent_prefix(agent):
        names.append(f"{prefix}_LLM_{key}")
    names.append(f"LLM_{key}")
    return _first_env(*names)


def _float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise LLMConfigError(f"expected a number, got {value!r}") from exc


def _int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise LLMConfigError(f"expected an integer, got {value!r}") from exc


def resolve_llm_config(agent: str | None = None) -> LLMConfig:
    """Build an :class:`LLMConfig` from the environment for ``agent``."""

    provider = (_lookup("PROVIDER", agent) or "openai").lower()

    model = _lookup("MODEL", agent) or _first_env(*_LEGACY_MODEL_ENV)

    api_key = _lookup("API_KEY", agent)
    if not api_key:
        api_key = _first_env(*_LEGACY_KEY_ENV.get(provider, ("API_KEY",)))

    base_url = _lookup("BASE_URL", agent) or _first_env("OPENAI_BASE_URL")

    timeout = _float(_lookup("TIMEOUT_SECONDS", agent), 60.0)
    max_retries = _int(_lookup("MAX_RETRIES", agent), 2)
    max_tokens = _int(_lookup("MAX_TOKENS", agent), 4096)

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout,
        max_retries=max_retries,
        max_tokens=max_tokens,
        agent=agent,
    )


__all__ = ["LLMConfig", "resolve_llm_config"]
