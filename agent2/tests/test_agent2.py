"""Tests for Agent 2 (Prosecutor). No network access - uses FakeProvider."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import agent2.server as server
from agent2 import Prosecutor, ProsecutorOutput
from agent2.server import app
from llm.testing import FakeProvider, use_fake_llm


@pytest.fixture(autouse=True)
def _reset_server_singleton():
    server._prosecutor = None
    yield
    server._prosecutor = None

SAMPLE_PRODUCT = {
    "name": "SmartPay Fraud Detection",
    "description": "Analyzes financial transactions to identify potential fraud.",
    "features": ["Detects suspicious transactions", "Generates a fraud risk score"],
}
SAMPLE_PATENTS = [
    {"id": "US123456", "summary": "Detecting fraud via behavioral analysis.", "claims": "Claim 1: ..."},
    {"id": "US345678", "summary": "Risk scores from historical transactions.", "claims": "Claim 1: ..."},
]

SAMPLE_OUTPUT = {
    "risk_claims": [
        {"patent_id": "US123456", "claim_id": "1", "risk_level": "medium", "reason": "behavioral analysis appears to correspond"}
    ],
    "claim_element_mappings": [
        {
            "patent_id": "US123456",
            "claim_id": "1",
            "claim_element": "analyzing transaction behavior",
            "product_feature": "Analyzes user transaction behavior",
            "strength": "moderate",
            "explanation": "could read on the supplied feature",
        }
    ],
    "confidence_per_patent": [
        {"patent_id": "US123456", "confidence": 0.6, "explanation": "partial mapping"}
    ],
}


def test_analyze_returns_structured_output():
    with use_fake_llm(responses=[json.dumps(SAMPLE_OUTPUT)]):
        result = Prosecutor().analyze(SAMPLE_PRODUCT, SAMPLE_PATENTS)
    assert isinstance(result, ProsecutorOutput)
    assert result.risk_claims[0].patent_id == "US123456"
    assert 0.0 <= result.confidence_per_patent[0].confidence <= 1.0


def test_analyze_requests_json_mode():
    with use_fake_llm(responses=[json.dumps(SAMPLE_OUTPUT)]):
        Prosecutor().analyze(SAMPLE_PRODUCT, SAMPLE_PATENTS)
        assert FakeProvider.calls[0]["response_format"] == {"type": "json_object"}


def test_stream_yields_tokens_then_result():
    with use_fake_llm(responses=[json.dumps(SAMPLE_OUTPUT)]):
        events = list(Prosecutor().stream(SAMPLE_PRODUCT, SAMPLE_PATENTS))
    assert events[0]["type"] == "token"
    assert events[-1]["type"] == "result"
    assert events[-1]["data"]["risk_claims"][0]["patent_id"] == "US123456"


def test_http_analyze_endpoint():
    with use_fake_llm(responses=[json.dumps(SAMPLE_OUTPUT)]):
        client = TestClient(app)
        resp = client.post("/analyze", json={"product": SAMPLE_PRODUCT, "patents": SAMPLE_PATENTS})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["result"]["risk_claims"][0]["patent_id"] == "US123456"


def test_http_analyze_requires_at_least_one_patent():
    client = TestClient(app)
    resp = client.post("/analyze", json={"product": SAMPLE_PRODUCT, "patents": []})
    assert resp.status_code == 422


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"
