"""Final report agent tests - scripted FakeProvider, no network."""

from __future__ import annotations

import json

from llm.testing import use_fake_llm
from report_agent import LEGAL_DISCLAIMER, ReportGenerator
from report_agent.agent import _fallback_narrative

FEATURES = {
    "product": {"name": "SmartCap Bottle", "summary": "Cap senses temperature, streams over BLE."},
    "features": [{"id": "F1", "name": "Temperature sensor in the cap", "function": "measure"}],
}
PATENTS = [{"patent_number": "US1", "title": "Sensing cap", "abstract": "A cap with a sensor.", "assignee": "Acme"}]
PROSECUTOR = {
    "claim_element_mappings": [
        {"patent_id": "US1", "claim_element": "a temperature sensor", "product_feature": "Temperature sensor in the cap"}
    ],
    "risk_claims": [{"patent_id": "US1", "claim_id": "1", "risk_level": "high", "reason": "reads on"}],
}
DEFENDER = {"distinctions": [{"claim_element": "BLE", "distinction": "no wireless in art", "reasoning": "x"}]}
RISK_MATRIX = {
    "overall_risk": "MEDIUM",
    "risks": [{"claim_element": "a temperature sensor", "risk_level": "HIGH", "reason": "central + disclosed"}],
}
DESIGN = {"alternatives": [{"id": 1, "description": "relocate sensor", "design_generation_prompt": "before/after"}]}

NARRATIVE = {
    "executive_summary": "Overall exposure appears medium based on the supplied information.",
    "key_risks": ["The temperature sensor element may read on US1."],
    "important_uncertainties": ["Claim construction not reviewed by counsel."],
    "recommended_next_steps": ["Consult a patent attorney."],
    "attorney_questions": ["Does our cap sensor fall within claim 1 of US1?"],
}


def _generate():
    return ReportGenerator().generate(
        feature_extraction=FEATURES,
        patents=PATENTS,
        prosecutor=PROSECUTOR,
        defender=DEFENDER,
        risk_matrix=RISK_MATRIX,
        design=DESIGN,
        images=[{"option_id": 1, "image_url": "/media/x.png"}],
    )


def test_report_assembles_passthrough_and_narrative():
    with use_fake_llm(responses=[json.dumps(NARRATIVE)]):
        report = _generate()

    assert report.executive_summary.startswith("Overall exposure")
    assert report.attorney_questions == ["Does our cap sensor fall within claim 1 of US1?"]
    # passthrough sections are always populated from code, not the model
    assert report.top_patents == PATENTS
    assert report.claim_mappings == PROSECUTOR["claim_element_mappings"]
    assert report.risk_matrix == RISK_MATRIX
    assert report.design_alternatives == DESIGN["alternatives"]
    assert report.redesign_concepts[0]["option_id"] == 1
    assert report.legal_disclaimer == LEGAL_DISCLAIMER


def test_report_survives_llm_failure_with_deterministic_fallback():
    with use_fake_llm(responses=["not valid json at all"]):
        report = _generate()

    assert report.legal_disclaimer == LEGAL_DISCLAIMER
    assert report.key_risks
    assert report.attorney_questions
    assert "US1" in " ".join(report.attorney_questions)
    assert report.top_patents == PATENTS  # passthrough still intact


def test_fallback_narrative_is_self_contained():
    narrative = _fallback_narrative(RISK_MATRIX, PROSECUTOR, DEFENDER)
    assert narrative.executive_summary
    assert len(narrative.important_uncertainties) >= 3
    assert narrative.recommended_next_steps
