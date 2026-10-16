"""Tests for Agent 4 (Design-Around Engineer). No network - uses FakeProvider."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import agent4.server as server
from agent4 import DesignEngineer, DesignOutput
from agent4.server import app
from llm.testing import FakeProvider, use_fake_llm

PRODUCT = {"name": "Smart Bottle", "description": "Senses liquid temperature.", "features": ["temp sensor in cap"]}
PROSECUTOR = {"risk_claims": [], "claim_element_mappings": [], "confidence_per_patent": []}
DEFENDER = {"distinctions": [], "prior_art_gaps": [], "weak_claim_elements": []}


def _alt(i: int) -> dict:
    return {
        "id": i,
        "description": f"Alternative {i} description",
        "avoids_claim_element": "temperature sensor in the cap",
        "changes_from_original": ["move sensor to the body"],
        "tradeoff": "slightly harder to service",
        "why_it_differs": "sensor is no longer in the cap",
        "risk_reduction_rationale": "changes the identified claim element; requires legal review",
        "design_generation_prompt": "engineering concept sketch, before vs after",
    }


SAMPLE = {
    "agent": "design-engineer",
    "status": "completed",
    "alternatives": [_alt(1), _alt(2), _alt(3)],
    "legal_disclaimer": "Not a determination of infringement or freedom to operate.",
}


@pytest.fixture(autouse=True)
def _reset_singleton():
    server._engineer = None
    yield
    server._engineer = None


def test_generate_returns_three_alternatives():
    with use_fake_llm(responses=[json.dumps(SAMPLE)]):
        result = DesignEngineer().generate(PRODUCT, PROSECUTOR, DEFENDER)
    assert isinstance(result, DesignOutput)
    assert len(result.alternatives) == 3
    assert result.alternatives[0].avoids_claim_element


def test_generate_requests_json_mode():
    with use_fake_llm(responses=[json.dumps(SAMPLE)]):
        DesignEngineer().generate(PRODUCT, PROSECUTOR, DEFENDER)
        assert FakeProvider.calls[0]["response_format"] == {"type": "json_object"}


def test_http_design_endpoint():
    with use_fake_llm(responses=[json.dumps(SAMPLE)]):
        client = TestClient(app)
        resp = client.post(
            "/design",
            json={"product": PRODUCT, "prosecutor": PROSECUTOR, "defender": DEFENDER},
        )
    assert resp.status_code == 200
    assert len(resp.json()["alternatives"]) == 3


def test_stream_yields_result_event():
    with use_fake_llm(responses=[json.dumps(SAMPLE)]):
        events = list(DesignEngineer().stream(PRODUCT, PROSECUTOR, DEFENDER))
    assert events[-1]["type"] == "result"
    assert len(events[-1]["data"]["alternatives"]) == 3


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"
