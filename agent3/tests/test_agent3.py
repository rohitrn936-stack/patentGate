"""Tests for Agent 3 (Defender).

These tests mock the OpenAI API so they never make real API calls and never
require network access. They exercise the FastAPI endpoints and the response
schema. Agent 3 uses OpenAI (not Claude/Anthropic, not Gemini).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agent3.agent import Defender
from agent3.schemas import DefenseAnalysis, WeakClaimElement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sample_agent2_output() -> dict:
    """Representative Agent 2 (Prosecutor) output."""
    return {
        "status": "ok",
        "invention": "A smart water bottle that measures liquid temperature "
        "using a sensor and sends it to a smartphone via Bluetooth.",
        "claim_elements": [
            {"id": "C1", "element": "A water bottle with a cap"},
            {"id": "C2", "element": "A temperature sensor in the cap"},
            {
                "id": "C3",
                "element": "Bluetooth transmission of temperature to a smartphone",
            },
        ],
        "prior_art": [
            {
                "id": "PA1",
                "title": "Smart beverage container with temperature sensing",
                "description": "A bottle cap temperature sensor that displays "
                "temperature on a built-in screen.",
                "similarity": 0.7,
            }
        ],
        "prior_art_concepts": [
            {"name": "Wireless sensor telemetry", "similarity": 0.5}
        ],
    }


def sample_analysis_json() -> dict:
    return {
        "distinctions": [
            {
                "claim_element": "Bluetooth transmission of temperature to a smartphone",
                "distinction": "Prior art only displays temperature on the "
                "bottle itself; this invention wirelessly transmits it.",
                "reasoning": "The prior-art reference uses a built-in screen and "
                "does not disclose Bluetooth transmission.",
            }
        ],
        "prior_art_gaps": [
            {
                "claim_element": "Bluetooth transmission",
                "gap": "Prior art does not disclose wireless transmission to a "
                "paired smartphone.",
                "reasoning": "No wireless interface is present in the supplied "
                "prior art.",
            }
        ],
        "weak_claim_elements": [
            {
                "claim_element": "A water bottle with a cap",
                "reasoning": "This is a generic, well-known element and is "
                "likely to be anticipated.",
                "risk": "high",
            },
            {
                "claim_element": "A temperature sensor in the cap",
                "reasoning": "Temperature sensing in a cap is disclosed by the "
                "prior art.",
                "risk": "medium",
            },
        ],
        "overall_assessment": "The wireless transmission distinction is the "
        "strongest defense; the bottle and cap-sensor elements are weak.",
        "confidence": 0.7,
        "disclaimer": "This is an AI-based analysis and is NOT a verified "
        "patent search or legal opinion.",
    }


def make_completion(data: dict):
    """Build an OpenAI-like chat completion response object."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))]
    )


@pytest.fixture()
def client():
    """A TestClient with OpenAI mocked."""
    from agent3 import server

    defender = Defender(api_key="sk-test-not-real")

    def fake_analyze(payload):
        return DefenseAnalysis.model_validate(sample_analysis_json())

    with mock.patch.object(defender, "analyze", side_effect=fake_analyze):
        server._defender = defender
        yield TestClient(server.app)


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_ok(client):
    response = client.post("/analyze", json=sample_agent2_output())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "defense_analysis" in data
    da = data["defense_analysis"]
    assert da["distinctions"]
    assert da["prior_art_gaps"]
    assert da["weak_claim_elements"]


def test_analyze_wrapped_under_agent2_output(client):
    response = client.post(
        "/analyze",
        json={"agent2_output": sample_agent2_output()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_empty_body(client):
    response = client.post("/analyze", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["errors"]


# ---------------------------------------------------------------------------
# Response schema tests
# ---------------------------------------------------------------------------


def test_response_schema_valid(client):
    response = client.post("/analyze", json=sample_agent2_output())
    data = response.json()
    assert data["defense_analysis"]["confidence"] is not None
    for item in data["defense_analysis"]["weak_claim_elements"]:
        assert item["risk"] in ("low", "medium", "high")


def test_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        DefenseAnalysis(confidence=1.5)


def test_risk_must_be_valid():
    with pytest.raises(ValidationError):
        WeakClaimElement(claim_element="x", risk="extreme")


# ---------------------------------------------------------------------------
# OpenAI API interaction tests (mocked)
# ---------------------------------------------------------------------------


def test_defender_calls_openai():
    defender = Defender(api_key="sk-test-not-real")
    fake_completion = make_completion(sample_analysis_json())
    with mock.patch.object(
        defender._client.chat.completions, "create", return_value=fake_completion
    ) as mocked:
        result = defender.analyze(sample_agent2_output())

    assert mocked.called
    assert isinstance(result, DefenseAnalysis)
    assert result.distinctions[0].claim_element.startswith("Bluetooth")
    assert 0.0 <= result.confidence <= 1.0


def test_defender_uses_json_mode():
    defender = Defender(api_key="sk-test-not-real")
    fake_completion = make_completion(sample_analysis_json())
    with mock.patch.object(
        defender._client.chat.completions, "create", return_value=fake_completion
    ) as mocked:
        defender.analyze(sample_agent2_output())
    assert mocked.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_defender_requires_api_key():
    # Correctly patch env so no key is available.
    with mock.patch.dict("os.environ", {}, clear=True), mock.patch(
        "agent3.agent.load_dotenv", return_value=None
    ):
        with pytest.raises(RuntimeError):
            Defender(api_key="")


def test_default_model_used_when_unset():
    with mock.patch.dict("os.environ", {}, clear=True), mock.patch(
        "agent3.agent.load_dotenv", return_value=None
    ):
        defender = Defender(api_key="sk-test-not-real", model="")
        assert defender._model == "gpt-4o-mini"


def test_no_patent_identifiers_in_output(client):
    response = client.post("/analyze", json=sample_agent2_output())
    da = response.json()["defense_analysis"]
    assert "patent_number" not in da
    assert "publication_number" not in da
    assert "url" not in da