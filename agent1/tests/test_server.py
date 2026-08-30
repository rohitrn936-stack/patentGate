"""Tests for the local HTTP API server (server.py).

These tests mock the OpenAI-backed Agent 1 pipeline so they never make a real
API call and never require network access. They use FastAPI/Starlette's
TestClient (httpx).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from agent1 import server
from agent1.schemas import KnowledgeAnalysis, SimilarConcept


@pytest.fixture()
def client(monkeypatch, tmp_path):
    """A TestClient whose Agent 1 pipeline is mocked and whose results.json is
    written into a temp directory (so real runs are never clobbered)."""
    # Redirect results.json writes to a temp dir.
    monkeypatch.setattr(server, "RESULTS_DIR", str(tmp_path))

    def fake_run(description, **kwargs):
        return SimpleNamespace(
            model_dump=lambda: {
                "status": "ok",
                "errors": [],
                "product": {
                    "name": "SmartCap Bottle",
                    "summary": "A smart water bottle.",
                },
                "analysis": {
                    "invention": description,
                    "technical_features": ["Temperature sensor"],
                    "similar_known_concepts": [],
                    "similarity_score": 0.5,
                    "similarity_explanation": "...",
                    "potentially_overlapping_areas": [],
                    "confidence": 0.5,
                    "disclaimer": "This analysis is based on the model's "
                    "learned knowledge and is NOT a verified patent search.",
                },
            }
        )

    monkeypatch.setattr(server, "run_agent1", fake_run)
    return TestClient(server.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_structured_json(client):
    response = client.post(
        "/analyze",
        json={"product_description": "A smart water bottle with a sensor."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["product"]["name"] == "SmartCap Bottle"
    assert "analysis" in data


def test_analyze_writes_results_file(client, tmp_path):
    client.post(
        "/analyze",
        json={"product_description": "A smart water bottle with a sensor."},
    )
    results_path = tmp_path / "results.json"
    assert results_path.exists()
    saved = json.loads(results_path.read_text(encoding="utf-8"))
    assert saved["status"] == "ok"
    assert saved["product"]["name"] == "SmartCap Bottle"


def test_analyze_rejects_empty_description(client):
    response = client.post("/analyze", json={"product_description": "   "})
    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_analyze_requires_product_description_field(client):
    response = client.post("/analyze", json={})
    assert response.status_code == 422