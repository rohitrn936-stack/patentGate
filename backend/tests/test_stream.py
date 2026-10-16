"""SSE streaming endpoint: event ordering + auth."""

from __future__ import annotations

import json

import pytest

from llm.registry import reset_provider_cache
from llm.testing import FakeProvider
from tests.test_pipeline import _SCRIPT

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _script_llm():
    FakeProvider.script(_SCRIPT)
    reset_provider_cache()
    yield
    FakeProvider.script([])
    reset_provider_cache()


async def _make_analysis(client):
    product = (
        await client.post(
            "/api/products",
            json={"name": "Smart bottle", "description": "Senses liquid temperature over Bluetooth."},
        )
    ).json()
    return (
        await client.post("/api/analyses", json={"product_id": product["id"]})
    ).json()


async def _collect_events(client, url) -> list[dict]:
    events: list[dict] = []
    async with client.stream("GET", url) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


async def test_stream_emits_ordered_events(auth_client):
    client, session = auth_client
    token = session["access_token"]
    analysis = await _make_analysis(client)

    events = await _collect_events(client, f"/api/analyses/{analysis['id']}/stream?token={token}")
    types = [e["type"] for e in events]

    for expected in (
        "USER_INPUT",
        "FEATURE_EXTRACTION_COMPLETED",
        "PATENT_SEARCH_STARTED",
        "PATENT_FOUND",
        "PROSECUTOR_COMPLETED",
        "DEFENDER_COMPLETED",
        "DESIGN_OPTIONS_GENERATED",
        "RISK_MATRIX_READY",
        "FINAL_REPORT_READY",
        "PIPELINE_COMPLETED",
    ):
        assert expected in types, f"missing {expected} in {types}"

    assert types.count("PATENT_FOUND") == 5
    assert types.index("FEATURE_EXTRACTION_COMPLETED") < types.index("PATENT_SEARCH_STARTED")
    assert types.index("PROSECUTOR_COMPLETED") < types.index("DEFENDER_COMPLETED")
    assert types.index("FINAL_REPORT_READY") < types.index("PIPELINE_COMPLETED")
    assert "ERROR" not in types

    # the analysis is persisted and rehydratable after the stream ends
    detail = (await client.get(f"/api/analyses/{analysis['id']}")).json()
    assert detail["status"] == "completed"
    assert detail["report"]["attorney_questions"]


async def test_stream_requires_a_valid_token(auth_client):
    client, _ = auth_client
    analysis = await _make_analysis(client)

    missing = await client.get(f"/api/analyses/{analysis['id']}/stream")
    assert missing.status_code == 422  # query param required

    bad = await client.get(f"/api/analyses/{analysis['id']}/stream?token=nonsense")
    assert bad.status_code == 401
