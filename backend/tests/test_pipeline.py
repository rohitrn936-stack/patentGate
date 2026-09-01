"""End-to-end orchestration test: create product -> run pipeline -> read result.

The LLM layer is the in-memory FakeProvider (conftest sets LLM_PROVIDER=fake),
scripted with one valid payload per agent call.
"""

from __future__ import annotations

import json

import pytest

from llm.registry import reset_provider_cache
from llm.testing import FakeProvider

pytestmark = pytest.mark.asyncio

_FEATURE_EXTRACTION = {
    "product": {"name": "SmartCap Bottle", "summary": "Senses liquid temperature."},
    "components": [{"id": "C1", "name": "cap"}],
    "features": [
        {"id": "F1", "name": "Temperature sensor in the cap", "description": "senses temp",
         "component": "cap", "function": "measure", "evidence": "user stated",
         "evidence_source": "user_stated", "confidence": 1.0}
    ],
    "assumptions": [],
}
_KNOWLEDGE = {
    "invention": "A bottle that senses temperature and reports over Bluetooth.",
    "technical_features": ["Temperature sensor in the cap"],
    "similar_known_concepts": [
        {"name": "Smart beverage container", "why_similar": "cap sensor",
         "matching_features": ["Temperature sensor in the cap"], "differences": "no BLE",
         "similarity_score": 0.8}
    ],
    "similarity_score": 0.7,
    "similarity_explanation": "well known",
    "potentially_overlapping_areas": ["smart drinkware"],
    "confidence": 0.6,
    "disclaimer": "This analysis is based on the model's learned knowledge and is NOT a verified patent search.",
}
_PROSECUTOR = {
    "risk_claims": [
        {"patent_id": "CONCEPT-1", "claim_id": "1", "risk_level": "medium", "reason": "could read on"}
    ],
    "claim_element_mappings": [
        {"patent_id": "CONCEPT-1", "claim_id": "1", "claim_element": "temperature sensor",
         "product_feature": "Temperature sensor in the cap", "strength": "moderate",
         "explanation": "appears to correspond"}
    ],
    "confidence_per_patent": [
        {"patent_id": "CONCEPT-1", "confidence": 0.5, "explanation": "partial mapping"}
    ],
}
_DEFENDER = {
    "distinctions": [
        {"claim_element": "Bluetooth transmission", "distinction": "prior art has no BLE",
         "reasoning": "no wireless disclosed"}
    ],
    "prior_art_gaps": [],
    "weak_claim_elements": [
        {"claim_element": "temperature sensor", "reasoning": "generic", "risk": "high"}
    ],
    "overall_assessment": "wireless is the strongest distinction",
    "confidence": 0.6,
    "disclaimer": "This is an AI-based analysis and is NOT a verified patent search or legal opinion.",
}
_DESIGN = {
    "agent": "design-engineer",
    "status": "completed",
    "alternatives": [
        {
            "id": i,
            "description": f"Alternative {i}: relocate the sensor",
            "avoids_claim_element": "temperature sensor in the cap",
            "changes_from_original": ["move sensor into the bottle body"],
            "tradeoff": "harder to service",
            "why_it_differs": "sensor is no longer in the cap",
            "risk_reduction_rationale": "changes the identified claim element; requires legal review",
            "design_generation_prompt": "engineering concept sketch before vs after",
        }
        for i in (1, 2, 3)
    ],
    "legal_disclaimer": "Not a determination of infringement or freedom to operate.",
}

_REPORT = {
    "executive_summary": "Overall exposure appears medium based on the supplied information.",
    "key_risks": ["The temperature-sensor element may read on CONCEPT-1."],
    "important_uncertainties": ["Claim construction has not been reviewed by counsel."],
    "recommended_next_steps": ["Consult a qualified patent attorney."],
    "attorney_questions": ["Does the cap sensor fall within the identified claim element?"],
}

_SCRIPT = [
    json.dumps(_FEATURE_EXTRACTION),
    json.dumps(_KNOWLEDGE),
    json.dumps(_PROSECUTOR),
    json.dumps(_DEFENDER),
    json.dumps(_DESIGN),
    json.dumps(_REPORT),
]


@pytest.fixture(autouse=True)
def _script_llm():
    FakeProvider.script(_SCRIPT)
    reset_provider_cache()
    yield
    FakeProvider.script([])
    reset_provider_cache()


async def test_full_pipeline_runs_and_persists(auth_client):
    client, _ = auth_client

    product = (
        await client.post(
            "/api/products",
            json={"name": "Smart bottle", "description": "Senses liquid temperature and sends it over Bluetooth."},
        )
    ).json()

    analysis = (
        await client.post("/api/analyses", json={"product_id": product["id"]})
    ).json()
    assert analysis["status"] == "pending"

    run = await client.post(f"/api/analyses/{analysis['id']}/run")
    assert run.status_code == 202

    # Starlette background tasks complete before the ASGI response returns.
    detail = await client.get(f"/api/analyses/{analysis['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed", body
    assert body["feature_extraction"]["product"]["name"] == "SmartCap Bottle"
    assert body["prosecutor"]["risk_claims"][0]["patent_id"] == "CONCEPT-1"
    assert body["defender"]["weak_claim_elements"][0]["risk"] == "high"
    assert len(body["design"]["alternatives"]) == 3
    assert "risk_matrix" in body["design"]
    assert body["errors"] == []

    # new stages: patent search + risk matrix + final report are all exposed
    assert len(body["patents"]) == 5
    assert body["patents"][0]["patent_number"].startswith("CONCEPT-")
    assert body["risk_matrix"]["overall_risk"] in {"LOW", "MEDIUM", "HIGH"}
    assert body["report"]["legal_disclaimer"].startswith("This analysis is AI-generated")
    assert body["report"]["attorney_questions"]


async def test_pipeline_marks_failed_when_an_agent_errors(auth_client):
    client, _ = auth_client
    # Only two valid responses, then invalid -> prosecutor structured parse fails.
    FakeProvider.script([json.dumps(_FEATURE_EXTRACTION), json.dumps(_KNOWLEDGE), "not json", "not json"])
    reset_provider_cache()

    product = (
        await client.post("/api/products", json={"name": "P", "description": "d"})
    ).json()
    analysis = (
        await client.post("/api/analyses", json={"product_id": product["id"]})
    ).json()
    await client.post(f"/api/analyses/{analysis['id']}/run")

    body = (await client.get(f"/api/analyses/{analysis['id']}")).json()
    assert body["status"] == "failed"
    assert body["errors"], body


async def test_run_conflicts_while_in_progress(auth_client, monkeypatch):
    client, _ = auth_client
    product = (
        await client.post("/api/products", json={"name": "P", "description": "d"})
    ).json()
    analysis = (
        await client.post("/api/analyses", json={"product_id": product["id"]})
    ).json()

    # Simulate an in-flight run by forcing a non-runnable status.
    from sqlalchemy import update

    from app.database import AsyncSessionLocal
    from app.models import Analysis

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Analysis).where(Analysis.id == analysis["id"]).values(status="analysis")
        )
        await db.commit()

    resp = await client.post(f"/api/analyses/{analysis['id']}/run")
    assert resp.status_code == 409
