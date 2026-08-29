import unittest

from claimbreaker.models import EvidenceType, FeatureExtractionResult, TechnicalFeature
from claimbreaker.patent_search import GOOGLE_PATENTS_SEARCH_URL, GooglePatentsSearch, generate_queries


def extraction() -> FeatureExtractionResult:
    return FeatureExtractionResult(
        product_summary="A helmet detects impacts and alerts a smartphone.",
        domain=["wearable safety device"],
        features=[
            TechnicalFeature(id="F1", name="impact detection", description="Detects sudden helmet impacts.", technical_components=["accelerometer"], function="Detect impact acceleration.", relationships=["F1 -> F2"], evidence_type=EvidenceType.EXPLICIT),
            TechnicalFeature(id="F2", name="wireless emergency alert", description="Sends an alert to a smartphone.", technical_components=["wireless transmitter"], function="Transmit emergency notification.", relationships=[], evidence_type=EvidenceType.EXPLICIT),
        ],
        search_terms=["helmet impact detection", "accelerometer smartphone alert", "wireless emergency notification"],
        technical_keywords=["crash detection", "inertial sensor", "mobile alert"],
        uncertainties=["Wireless protocol is unspecified."],
    )


def google_payload():
    return {"results": {"cluster": [{"result": [
        {"id": "patent/US11111111A1/en", "patent": {"publication_number": "US11111111A1", "title": "Helmet impact detection and wireless emergency alert", "snippet": "An accelerometer detects an impact and sends a smartphone notification.", "publication_date": "2023-01-02"}},
        {"id": "patent/US11111111A1/en", "patent": {"publication_number": "US11111111A1", "title": "Helmet impact detection and wireless emergency alert", "snippet": "Duplicate result.", "publication_date": "2023-01-02"}},
        {"id": "patent/US22222222A1/en", "patent": {"publication_number": "US22222222A1", "title": "Decorative helmet", "snippet": "A helmet shell.", "publication_date": "2022-05-01"}},
        {"id": "patent/US33333333A1/en", "patent": {"title": "Missing publication number", "snippet": "Ignored."}},
    ]}]}}


class FakeResponse:
    def __init__(self, payload=None, error=None): self.payload, self.error = payload, error
    def raise_for_status(self):
        if self.error: raise self.error
    def json(self): return self.payload


class FakeClient:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def get(self, url, *, params):
        self.calls.append((url, params))
        return self.responses.pop(0)


class PatentSearchTests(unittest.TestCase):
    def test_generates_three_to_five_focused_queries(self):
        queries = generate_queries(extraction())
        self.assertGreaterEqual(len(queries), 3)
        self.assertLessEqual(len(queries), 5)
        self.assertIn("helmet impact detection", queries[0])

    def test_parses_deduplicates_ranks_and_selects_candidates(self):
        queries = generate_queries(extraction())
        client = FakeClient([FakeResponse(google_payload()) for _ in queries])
        result = GooglePatentsSearch(client).search(extraction())
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].patent_id, "US11111111A1")
        self.assertGreater(result.results[0].relevance_score, result.results[1].relevance_score)
        self.assertIn("accelerometer smartphone alert", result.results[0].matched_terms)
        self.assertTrue(result.results[0].url.startswith("https://patents.google.com/patent/"))
        self.assertTrue(all(call[0] == GOOGLE_PATENTS_SEARCH_URL for call in client.calls))

    def test_empty_results_are_returned_without_fabrication(self):
        queries = generate_queries(extraction())
        result = GooglePatentsSearch(FakeClient([FakeResponse({"results": {"cluster": []}}) for _ in queries])).search(extraction())
        self.assertEqual(result.results, [])
        self.assertEqual(result.warnings, [])

    def test_api_failure_becomes_warning(self):
        queries = generate_queries(extraction())
        import httpx
        client = FakeClient([FakeResponse(error=httpx.HTTPStatusError("bad gateway", request=None, response=None)) for _ in queries])
        result = GooglePatentsSearch(client).search(extraction())
        self.assertEqual(result.results, [])
        self.assertEqual(len(result.warnings), len(queries))

    def test_malformed_response_becomes_warning(self):
        queries = generate_queries(extraction())
        result = GooglePatentsSearch(FakeClient([FakeResponse([]) for _ in queries])).search(extraction())
        self.assertEqual(result.results, [])
        self.assertEqual(len(result.warnings), len(queries))
