"""Unit tests for Agent 1.

These tests never make real API calls and never use real API keys.
API clients are replaced with fakes or ``unittest.mock``. There is no
web search, Gemini, or external patent retrieval in Agent 1.
"""

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from pydantic import ValidationError

from agent1 import run_agent1
from agent1.extractor import FeatureExtractor, load_image_as_data_url
from agent1.schemas import (
    Agent1Output,
    Component,
    Feature,
    FeatureExtraction,
    KnowledgeAnalysis,
    Product,
    SimilarConcept,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sample_extraction() -> FeatureExtraction:
    """A realistic FeatureExtraction used across the tests."""
    return FeatureExtraction(
        product=Product(
            name="SmartCap Bottle",
            summary="A water bottle whose sensorized cap measures liquid "
            "temperature and streams it to a smartphone over Bluetooth.",
        ),
        components=[
            Component(
                id="C1",
                name="cap",
                description="Removable cap that hosts the electronics.",
                function="Seals the bottle and holds the sensor.",
            )
        ],
        features=[
            Feature(
                id="F1",
                name="Temperature sensor in the cap",
                description="Measures the temperature of the liquid.",
                component="cap",
                function="Makes contact with the liquid and senses its temperature.",
                evidence="User stated the cap contains a sensor measuring "
                "the temperature of the liquid.",
                evidence_source="user_stated",
                confidence=1.0,
            ),
            Feature(
                id="F2",
                name="Bluetooth transmission",
                description="Wireless link that sends temperature readings "
                "to a smartphone.",
                component="cap electronics",
                function="Transmits measurement data to a paired smartphone.",
                evidence="User stated the temperature is sent to a smartphone "
                "using Bluetooth.",
                evidence_source="user_stated",
                confidence=1.0,
            ),
        ],
        technical_concepts=[{"name": "temperature sensing", "description": ""}],
        mechanisms=[
            {"name": "contact thermometry", "description": "", "purpose": ""}
        ],
        materials=[],
        interfaces=[
            {
                "name": "Bluetooth",
                "interface_type": "wireless",
                "protocol": "Bluetooth",
                "description": "",
            }
        ],
        software_features=[
            {"name": "temperature reporting app", "description": ""}
        ],
        assumptions=[
            {
                "message": "The sensor contacts the liquid directly.",
                "reason": "The description does not say how the sensor touches "
                "the liquid.",
            }
        ],
    )


def sample_analysis() -> KnowledgeAnalysis:
    """A realistic KnowledgeAnalysis used across the tests."""
    return KnowledgeAnalysis(
        invention="A water bottle that senses liquid temperature and sends it "
        "to a smartphone over Bluetooth.",
        technical_features=["Temperature sensor in the cap", "Bluetooth transmission"],
        similar_known_concepts=[
            SimilarConcept(
                name="Smart beverage container with temperature sensing",
                why_similar="Known smart-bottle products measure liquid "
                "temperature with a sensor in the cap.",
                matching_features=["Temperature sensor in the cap"],
                differences="May not stream readings over Bluetooth in the "
                "same way.",
                similarity_score=0.85,
            ),
            SimilarConcept(
                name="Wireless sensor telemetry",
                why_similar="Bluetooth Low Energy is widely used to stream "
                "sensor readings to smartphones.",
                matching_features=["Bluetooth transmission"],
                differences="Generic telemetry, not bottle-specific.",
                similarity_score=0.6,
            ),
        ],
        similarity_score=0.75,
        similarity_explanation="The cap-mounted temperature sensor and "
        "Bluetooth reporting are well-known concepts in the smart-drinkware "
        "domain.",
        potentially_overlapping_areas=[
            "smart drinkware",
            "Bluetooth sensor telemetry",
            "temperature sensing",
        ],
        confidence=0.7,
        disclaimer="This analysis is based on the model's learned knowledge "
        "and is NOT a verified patent search.",
    )


class FakeExtractor:
    """Drop-in FeatureExtractor replacement that avoids the OpenAI API."""

    def extract_features(self, description, image_data_url=None):
        return sample_extraction()

    def analyze_similar_concepts(self, extraction, product_description):
        return sample_analysis()


class FailingExtractor:
    """An extractor whose analysis step fails, to test graceful degradation."""

    def extract_features(self, description, image_data_url=None):
        return sample_extraction()

    def analyze_similar_concepts(self, extraction, product_description):
        raise RuntimeError("503 upstream rate limit exceeded")


# ---------------------------------------------------------------------------
# 1. Pydantic output schema works
# ---------------------------------------------------------------------------


def test_output_schema_round_trip():
    output = Agent1Output(
        product=Product(name="SmartCap Bottle", summary="summary"),
        components=[Component(id="C1", name="cap")],
        features=[sample_extraction().features[0]],
        analysis=sample_analysis(),
    )
    payload = output.model_dump_json()
    reloaded = Agent1Output.model_validate_json(payload)
    assert reloaded == output
    assert reloaded.analysis.similar_known_concepts[0].name.startswith("Smart")


# ---------------------------------------------------------------------------
# 2. A sample feature object can be created
# ---------------------------------------------------------------------------


def test_feature_model_creation():
    feature = Feature(
        id="F1",
        name="Temperature sensor",
        description="Senses liquid temperature.",
        component="cap",
        function="Measures temperature.",
        evidence="Stated by the user.",
        evidence_source="user_stated",
        confidence=0.95,
    )
    assert feature.id == "F1"
    assert feature.evidence_source == "user_stated"
    assert feature.confidence == 0.95


def test_feature_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        Feature(id="F1", name="x", confidence=1.5)


def test_similarity_score_bounds_enforced():
    with pytest.raises(ValidationError):
        SimilarConcept(name="x", similarity_score=1.5)


def test_analysis_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        KnowledgeAnalysis(confidence=-0.5)


# ---------------------------------------------------------------------------
# 3. Agent 1 handles empty input appropriately
# ---------------------------------------------------------------------------


def test_empty_description_raises():
    with pytest.raises(ValueError):
        run_agent1("  ", load_env=False)


def test_missing_image_path_raises():
    with pytest.raises(FileNotFoundError):
        run_agent1(
            "A bottle",
            image_path="does_not_exist.png",
            extractor=FakeExtractor(),
            load_env=False,
        )


def test_unsupported_image_type_raises(tmp_path):
    bogus = tmp_path / "image.txt"
    bogus.write_text("not really an image")
    with pytest.raises(ValueError):
        load_image_as_data_url(str(bogus))


def test_supported_image_becomes_data_url(tmp_path):
    image = tmp_path / "pic.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 16)
    data_url = load_image_as_data_url(str(image))
    assert data_url.startswith("data:image/png;base64,")


# ---------------------------------------------------------------------------
# 4. The application does not require an image
# ---------------------------------------------------------------------------


def test_runs_without_image():
    output = run_agent1(
        "Create a water bottle that measures the temperature of the liquid "
        "using a sensor in the cap and sends it to a smartphone with Bluetooth.",
        extractor=FakeExtractor(),
        load_env=False,
    )
    assert output.status == "ok"
    assert output.product.name == "SmartCap Bottle"
    assert [f.id for f in output.features] == ["F1", "F2"]
    analysis = output.analysis
    assert analysis.invention
    assert "Temperature sensor in the cap" in analysis.technical_features
    assert analysis.similar_known_concepts[0].name.startswith("Smart")
    assert analysis.disclaimer
    assert "NOT a verified patent search" in analysis.disclaimer


def test_analysis_failure_is_graceful():
    output = run_agent1(
        "Create a water bottle that measures the temperature of the liquid.",
        extractor=FailingExtractor(),
        load_env=False,
    )
    assert output.status == "analysis_failed"
    assert output.errors
    assert "Similar-concept analysis failed" in output.errors[0]
    # Features survive even though the analysis step crashed.
    assert output.product.name == "SmartCap Bottle"
    assert len(output.features) == 2
    assert output.analysis.similar_known_concepts == []


# ---------------------------------------------------------------------------
# 5. API calls can be mocked rather than making real API calls
# ---------------------------------------------------------------------------


def test_openai_extraction_call_is_mocked():
    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "product": {"name": "Mug", "summary": "S"},
            "components": [],
            "features": [],
            "technical_concepts": [],
            "mechanisms": [],
            "materials": [],
            "interfaces": [],
            "software_features": [],
            "assumptions": [],
        })))],
    )
    extractor = FeatureExtractor(api_key="sk-test-not-real", model="gpt-test")
    with mock.patch.object(
        extractor._client.chat.completions, "create", return_value=fake_completion
    ) as mocked:
        extraction = extractor.extract_features("A mug", image_data_url=None)
    assert mocked.called
    assert extraction.product.name == "Mug"


def test_openai_analysis_call_is_mocked():
    analysis_json = {
        "invention": "A smart mug that measures temperature.",
        "technical_features": ["Temperature sensor"],
        "similar_known_concepts": [
            {
                "name": "Smart mug with temperature sensing",
                "why_similar": "Existing smart mugs sense liquid temperature.",
                "matching_features": ["Temperature sensor"],
                "differences": "May not report wirelessly.",
                "similarity_score": 0.8,
            }
        ],
        "similarity_score": 0.8,
        "similarity_explanation": "Temperature-sensing drinkware is well known.",
        "potentially_overlapping_areas": ["smart drinkware"],
        "confidence": 0.7,
        "disclaimer": "This analysis is based on the model's learned knowledge "
        "and is NOT a verified patent search.",
    }
    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(analysis_json)))]
    )
    extractor = FeatureExtractor(api_key="sk-test-not-real", model="gpt-test")
    with mock.patch.object(
        extractor._client.chat.completions, "create", return_value=fake_completion
    ) as mocked:
        analysis = extractor.analyze_similar_concepts(sample_extraction(), "A mug")
    assert mocked.called
    assert analysis.invention
    assert analysis.similar_known_concepts[0].name == "Smart mug with temperature sensing"
    assert 0.0 <= analysis.similarity_score <= 1.0


# ---------------------------------------------------------------------------
# 6. No patent identifiers are ever fabricated
# ---------------------------------------------------------------------------


def test_similar_concept_has_no_patent_fields():
    concept = SimilarConcept(name="Smart mug")
    data = concept.model_dump()
    for key in (
        "publication_number",
        "patent_number",
        "filing_date",
        "publication_date",
        "url",
    ):
        assert key not in data