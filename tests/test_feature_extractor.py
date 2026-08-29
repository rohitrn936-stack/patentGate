import os
import unittest
from types import SimpleNamespace

from claimbreaker.feature_extractor import DEFAULT_MODEL, extract_features_from_image_bytes


def payload(summary: str, feature_name: str = "impact acceleration sensor"):
    return {
        "product_summary": summary,
        "domain": ["wearable safety device"],
        "features": [{
            "id": "F1", "name": feature_name,
            "description": "A sensor measures acceleration associated with an impact.",
            "technical_components": ["acceleration sensor"],
            "function": "Measure sudden acceleration.",
            "relationships": [], "evidence_type": "explicit",
        }],
        "search_terms": [feature_name, "impact detection sensor"],
        "technical_keywords": ["accelerometer", "inertial sensor"],
        "uncertainties": ["The description does not specify a wireless protocol."],
    }


class FakeResponses:
    def __init__(self, response): self.response, self.calls = response, []
    def parse(self, **kwargs): self.calls.append(kwargs); return self.response


class FakeClient:
    def __init__(self, result): self.responses = FakeResponses(SimpleNamespace(output_parsed=result))


class FeatureExtractorTests(unittest.TestCase):
    def test_smart_helmet_text_uses_openai_structured_output(self):
        client = FakeClient(payload("A helmet detects impacts using an acceleration sensor."))
        result = extract_features_from_image_bytes("A smart helmet detects impacts and sends an alert.", client=client)
        call = client.responses.calls[0]
        self.assertEqual(result.features[0].id, "F1")
        self.assertEqual(DEFAULT_MODEL, "gpt-5-nano")
        self.assertEqual(call["model"], "gpt-5-nano")
        self.assertEqual(call["text_format"].__name__, "FeatureExtractionResult")
        self.assertNotIn("infring", result.model_dump_json().lower())

    def test_openai_model_is_configurable(self):
        client = FakeClient(payload("A helmet detects impacts."))
        old = os.environ.get("OPENAI_MODEL")
        os.environ["OPENAI_MODEL"] = "test-model"
        try:
            extract_features_from_image_bytes("A smart helmet detects impacts.", client=client)
        finally:
            if old is None: os.environ.pop("OPENAI_MODEL", None)
            else: os.environ["OPENAI_MODEL"] = old
        self.assertEqual(client.responses.calls[0]["model"], "test-model")

    def test_water_bottle_text_and_image_use_openai_vision_format(self):
        client = FakeClient(payload("A bottle measures water intake.", "fluid level sensor"))
        result = extract_features_from_image_bytes("A smart water bottle tracks water intake.", b"png-bytes", "image/png", client=client)
        content = client.responses.calls[0]["input"][0]["content"]
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))
        self.assertEqual(result.features[0].name, "fluid level sensor")

    def test_consumer_device_and_uncertainties_validate(self):
        data = payload("A countertop device controls a heating element.", "temperature controller")
        data["domain"] = ["consumer appliance", "thermal control"]
        result = extract_features_from_image_bytes("A countertop appliance regulates heating.", client=FakeClient(data))
        self.assertTrue(result.uncertainties)
        self.assertTrue(result.search_terms)

    def test_malformed_model_output_does_not_pass_validation(self):
        invalid = payload("A helmet detects impacts.")
        invalid["features"][0]["id"] = "helmet-feature"
        with self.assertRaisesRegex(ValueError, "invalid Agent 1 payload"):
            extract_features_from_image_bytes("A helmet detects impacts.", client=FakeClient(invalid))
