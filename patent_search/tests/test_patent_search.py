"""Patent search layer tests - no network access.

A fake HTTP client returns scripted JSON payloads so the source parsers,
de-duplication, ranking and the offline fallback can all be exercised
deterministically.
"""

from __future__ import annotations

from patent_search import PatentSearchService, build_queries
from patent_search.schemas import PatentHit
from patent_search.service import _dedupe

AGENT1 = {
    "product": {"name": "SmartCap Bottle", "summary": "A bottle whose cap senses liquid temperature and streams it over Bluetooth."},
    "features": [
        {"id": "F1", "name": "Temperature sensor in the cap", "function": "measure liquid temperature"},
        {"id": "F2", "name": "Bluetooth transmission", "function": "send readings to a phone"},
    ],
    "mechanisms": [{"name": "thermistor contact sensing"}],
    "interfaces": [{"name": "Bluetooth Low Energy"}],
    "analysis": {
        "invention": "A bottle that senses temperature and reports over BLE.",
        "similar_known_concepts": [
            {
                "name": "Smart beverage container",
                "why_similar": "cap-mounted sensor",
                "matching_features": ["Temperature sensor in the cap"],
                "differences": "no BLE",
                "similarity_score": 0.8,
            }
        ],
        "similarity_explanation": "well-trodden smart-drinkware space",
        "potentially_overlapping_areas": ["smart drinkware"],
    },
}


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """Routes by URL to a scripted payload; records calls."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def _match(self, url):
        for key, payload in self.routes.items():
            if key in url:
                return payload
        return {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Resp(self._match(url))

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Resp(self._match(url))

    def close(self):
        pass


def test_build_queries_uses_features_not_raw_description():
    queries = build_queries(AGENT1)
    assert queries, "expected at least one query"
    joined = " ".join(queries).lower()
    assert "temperature" in joined and "bluetooth" in joined
    assert len(queries) <= 5


def test_patentsview_parsed_and_ranked():
    payload = {
        "error": False,
        "patents": [
            {
                "patent_id": "10123456",
                "patent_title": "Temperature sensing bottle cap with wireless link",
                "patent_abstract": "A cap containing a temperature sensor transmits readings over Bluetooth.",
                "patent_date": "2019-05-14",
                "patent_earliest_application_date": "2017-02-01",
                "assignees": [{"assignee_organization": "Hydration Labs Inc"}],
                "inventors": [{"inventor_name_first": "Ada", "inventor_name_last": "Lovelace"}],
            }
        ],
    }
    client = _FakeClient({"search.patentsview.org": payload})
    svc = PatentSearchService(client=client, config={"patentsview_api_key": "k", "allow_scrape": False})
    result = svc.search(AGENT1)

    assert "patentsview" in result.sources_used
    top = result.patents[0]
    assert top.patent_number == "10123456"
    assert top.assignee == "Hydration Labs Inc"
    assert top.inventors == ["Ada Lovelace"]
    assert top.filing_date == "2017-02-01"
    assert top.relevance_score > 0
    assert top.matching_features
    assert len(result.patents) == 5  # padded with derived stubs


def test_google_patents_fallback_when_no_keys():
    payload = {
        "results": {
            "cluster": [
                {
                    "result": [
                        {
                            "patent": {
                                "publication_number": "US9999999B2",
                                "title": "Wireless thermometer for containers",
                                "snippet": "A Bluetooth thermometer mounted in a container cap.",
                                "publication_date": "2018-01-02",
                            }
                        }
                    ]
                }
            ]
        }
    }
    client = _FakeClient({"patents.google.com/xhr/query": payload})
    svc = PatentSearchService(client=client)
    result = svc.search(AGENT1)
    assert "google_patents" in result.sources_used
    assert any(p.patent_number == "US9999999B2" for p in result.patents)


def test_offline_returns_five_derived_stubs():
    svc = PatentSearchService(config={"enabled": False})
    result = svc.search(AGENT1)
    assert result.sources_used == ["derived"]
    assert len(result.patents) == 5
    assert result.patents[0].source == "derived"
    assert result.patents[0].patent_number.startswith("CONCEPT-")
    assert result.warnings  # explains why network search was skipped


def test_dedupe_merges_by_number_and_title():
    hits = [
        PatentHit(patent_number="US1", title="Widget", abstract="short"),
        PatentHit(patent_number="US1", title="Widget", abstract="a much longer abstract body"),
        PatentHit(patent_number="US2", title="Other"),
    ]
    out = _dedupe(hits)
    assert len(out) == 2
    assert out[0].abstract == "a much longer abstract body"


def test_agent_patent_shape():
    hit = PatentHit(patent_number="US1", title="T", abstract="A")
    shaped = hit.as_agent_patent()
    assert shaped["id"] == "US1"
    assert "summary" in shaped and "claims" in shaped
