"""Tests for the provider-agnostic LLM layer.

No network access: real providers are exercised only for config/error-mapping
behaviour; completions run against the in-memory FakeProvider.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from pydantic import BaseModel

from llm import (
    LLMAuthError,
    LLMBadResponseError,
    LLMConfigError,
    LLMRateLimitError,
    Message,
    available_providers,
    get_llm,
    get_provider_class,
    reset_provider_cache,
    resolve_llm_config,
)
from llm.testing import FakeProvider, use_fake_llm


class Answer(BaseModel):
    answer: int
    note: str = ""


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith(("LLM_", "AGENT1_LLM_", "AGENT2_LLM_")) or key in {
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "ANTHROPIC_API_KEY",
            "API_KEY",
            "MODEL_NAME",
        }:
            monkeypatch.delenv(key, raising=False)
    reset_provider_cache()
    yield
    reset_provider_cache()


# -- registry ---------------------------------------------------------------


def test_builtin_providers_registered():
    names = available_providers()
    for expected in ("openai", "anthropic", "openrouter", "gemini", "local"):
        assert expected in names


def test_unknown_provider_raises():
    with pytest.raises(LLMConfigError):
        get_provider_class("does-not-exist")


# -- configuration resolution --------------------------------------------


def test_global_config_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-x")
    monkeypatch.setenv("LLM_API_KEY", "k-global")
    cfg = resolve_llm_config()
    assert (cfg.provider, cfg.model, cfg.api_key) == ("anthropic", "claude-x", "k-global")


def test_per_agent_override_wins(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("AGENT1_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("AGENT1_LLM_MODEL", "claude-x")
    cfg = resolve_llm_config("agent1")
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-x"
    # A different agent still gets the global default.
    assert resolve_llm_config("agent2").provider == "openai"


def test_legacy_openai_env_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-legacy")
    cfg = resolve_llm_config("agent1")
    assert cfg.provider == "openai"
    assert cfg.api_key == "sk-legacy"
    assert cfg.model == "gpt-legacy"


def test_legacy_generic_api_key_for_prosecutor(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("API_KEY", "sk-generic")
    assert resolve_llm_config("agent2").api_key == "sk-generic"


# -- provider instantiation / errors ------------------------------------


def test_openai_provider_requires_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(LLMConfigError):
        get_llm()


def test_local_provider_needs_no_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")
    llm = get_llm()
    assert llm.name == "local"
    assert llm.base_url == "http://localhost:11434/v1"


def test_openrouter_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_API_KEY", "or-key")
    llm = get_llm()
    assert llm.base_url == "https://openrouter.ai/api/v1"
    assert llm.model == "openai/gpt-4o-mini"


def test_openai_error_mapping(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "sk-x")
    llm = get_llm()

    import openai

    from llm.errors import LLMProviderError, LLMTimeoutError

    def _instance(cls):
        # Build a stand-in that passes isinstance() without the SDK's heavy
        # __init__ (which needs a real httpx response).
        return type(f"_T{cls.__name__}", (cls,), {"__init__": lambda self: None})()

    cases = [
        (openai.AuthenticationError, LLMAuthError),
        (openai.PermissionDeniedError, LLMAuthError),
        (openai.RateLimitError, LLMRateLimitError),
        (openai.APITimeoutError, LLMTimeoutError),
        (openai.APIConnectionError, LLMProviderError),
    ]
    for raised_cls, expected in cases:
        mapped = llm._map_error(_instance(raised_cls))
        assert isinstance(mapped, expected), (raised_cls, mapped)

    # And the mapping is actually applied on the call path.
    with mock.patch.object(
        llm._client.chat.completions, "create", side_effect=_instance(openai.RateLimitError)
    ):
        with pytest.raises(LLMRateLimitError):
            llm.complete([Message.user("hi")])


# -- completions via the fake provider --------------------------------


def test_fake_complete_and_usage():
    with use_fake_llm(responses=['{"answer": 1}']):
        llm = get_llm(agent="agent1")
        result = llm.complete([Message.system("s"), Message.user("u")])
    assert result.text == '{"answer": 1}'
    assert result.usage.total_tokens == 15
    assert FakeProvider.calls[0]["model"] == "fake-1"


def test_structured_output_parses_and_validates():
    with use_fake_llm(responses=['```json\n{"answer": 7, "note": "ok"}\n```']):
        result = get_llm(agent="agent1").complete_structured([Message.user("u")], Answer)
    assert isinstance(result, Answer)
    assert result.answer == 7 and result.note == "ok"


def test_structured_output_repair_round_trip():
    with use_fake_llm(responses=["not json at all", '{"answer": 9}']):
        result = get_llm(agent="agent1").complete_structured([Message.user("u")], Answer)
    assert result.answer == 9
    assert len(FakeProvider.calls) == 2  # original + one repair


def test_structured_output_gives_up_after_repair():
    with use_fake_llm(responses=["nope", "still nope"]):
        with pytest.raises(LLMBadResponseError):
            get_llm(agent="agent1").complete_structured([Message.user("u")], Answer)


def test_retry_then_succeed():
    with use_fake_llm(responses=[LLMRateLimitError("429"), '{"answer": 3}']):
        llm = get_llm(agent="agent1")
        llm.max_retries = 2
        with mock.patch("time.sleep"):
            result = llm.complete([Message.user("u")])
    assert result.text == '{"answer": 3}'


def test_non_retryable_error_propagates_immediately():
    with use_fake_llm(responses=[LLMAuthError("401"), '{"answer": 3}']):
        with pytest.raises(LLMAuthError):
            get_llm(agent="agent1").complete([Message.user("u")])


def test_stream_events():
    with use_fake_llm(responses=['{"answer": 5}']):
        events = list(get_llm(agent="agent1").stream([Message.user("u")]))
    assert events[0].type == "text"
    assert "".join(e.text for e in events if e.type == "text") == '{"answer": 5}'
    assert events[-1].type == "done"


def test_json_object_response_format_passed_for_openai_family():
    with use_fake_llm(responses=['{"answer": 1}']):
        get_llm(agent="agent1").complete_structured([Message.user("u")], Answer)
    assert FakeProvider.calls[0]["response_format"] == {"type": "json_object"}
