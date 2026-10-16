"""Provider registry + the :func:`get_llm` factory.

Adding a provider is: implement :class:`~llm.base.LLMProvider`, decorate it with
``@register_provider``, and import it from :mod:`llm.providers`. Nothing else in
the codebase needs to change.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TypeVar

from .base import LLMProvider
from .config import LLMConfig, resolve_llm_config
from .errors import LLMConfigError

logger = logging.getLogger("patentgate.llm")

_REGISTRY: dict[str, type[LLMProvider]] = {}

TProvider = TypeVar("TProvider", bound=type[LLMProvider])


def register_provider(cls: TProvider) -> TProvider:
    """Class decorator that adds ``cls`` to the registry under ``cls.name``."""

    name = getattr(cls, "name", "") or ""
    if not name:
        raise LLMConfigError(f"{cls.__name__} must define a non-empty 'name'")
    _REGISTRY[name.lower()] = cls
    return cls


def available_providers() -> list[str]:
    """Sorted list of registered provider names."""

    _ensure_builtin_providers()
    return sorted(_REGISTRY)


def get_provider_class(name: str) -> type[LLMProvider]:
    _ensure_builtin_providers()
    try:
        return _REGISTRY[name.lower()]
    except KeyError:
        raise LLMConfigError(
            f"unknown LLM provider {name!r}; available: {', '.join(sorted(_REGISTRY)) or '(none)'}"
        ) from None


def build_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate (uncached) the provider described by ``config``."""

    provider_cls = get_provider_class(config.provider)
    return provider_cls(
        api_key=config.api_key,
        model=config.model,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
        default_max_tokens=config.max_tokens,
        extra=config.extra,
    )


@lru_cache(maxsize=32)
def _cached_provider(cache_key: tuple) -> LLMProvider:
    # cache_key is (provider, model, api_key, base_url, timeout, retries, tokens, agent)
    (provider, model, api_key, base_url, timeout, retries, tokens, agent) = cache_key
    return build_provider(
        LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            max_retries=retries,
            max_tokens=tokens,
            agent=agent,
        )
    )


def get_llm(agent: str | None = None, *, config: LLMConfig | None = None) -> LLMProvider:
    """Return a ready-to-use provider for ``agent`` (or the global config).

    Instances are cached per resolved configuration, so repeated calls in a
    request are cheap. Pass ``config`` to bypass environment resolution.
    """

    cfg = config or resolve_llm_config(agent)
    key = (
        cfg.provider,
        cfg.model,
        cfg.api_key,
        cfg.base_url,
        cfg.timeout_seconds,
        cfg.max_retries,
        cfg.max_tokens,
        cfg.agent,
    )
    return _cached_provider(key)


def reset_provider_cache() -> None:
    """Drop cached provider instances (used by tests that mutate the env)."""

    _cached_provider.cache_clear()


_BUILTINS_LOADED = False


def _ensure_builtin_providers() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    try:
        from . import providers  # noqa: F401  (registers built-ins on import)
    except Exception:  # pragma: no cover - defensive
        logger.exception("failed to import built-in llm providers")


__all__ = [
    "register_provider",
    "available_providers",
    "get_provider_class",
    "build_provider",
    "get_llm",
    "reset_provider_cache",
]
