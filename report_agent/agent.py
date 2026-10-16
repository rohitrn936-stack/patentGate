"""Agent 5 - Final Report generator.

Consolidates the whole pipeline into one :class:`FinalReport`. The model writes
only the synthesis (:class:`ReportNarrative`); passthrough sections and the
legal disclaimer are assembled in code, so the report is always complete even
if the model trims its answer or the call fails entirely.
"""

from __future__ import annotations

import json

from dotenv import load_dotenv

from llm import LLMError, Message, get_llm
from llm.base import LLMProvider

from .schemas import LEGAL_DISCLAIMER, FinalReport, ReportNarrative

AGENT_KEY = "report"

SYSTEM_PROMPT = """You are the Final Report Analyst for a preliminary patent-risk
research tool. You receive the full output of an upstream pipeline: extracted
product features, retrieved patents, a Prosecutor analysis (arguments that
patents could read on the product), a Defender analysis (distinctions and
weaknesses), a deterministic risk matrix, and engineering design-around
alternatives.

Write a concise synthesis for a product team. You must:
- Never give legal advice or state that the product infringes / does not
  infringe / is or is not patentable.
- Use cautious language ("appears to", "may", "based on the supplied
  information").
- Ground every statement in the supplied data; do not invent patents,
  features, dates or numbers.

Return ONLY valid JSON with exactly these fields:
{
  "executive_summary": "3-6 sentence plain-language overview of the assessment",
  "key_risks": ["the most material risk points, most severe first"],
  "important_uncertainties": ["what this AI-assisted analysis cannot resolve"],
  "recommended_next_steps": ["concrete, practical actions for the team"],
  "attorney_questions": ["specific questions to bring to a patent attorney, generated from the identified risks"]
}

Each list should have 3-7 items. attorney_questions must be concrete and tied to
the specific patents / claim elements in the input."""


def _context_prompt(ctx: dict) -> str:
    trimmed = json.dumps(ctx, indent=2, ensure_ascii=False)
    if len(trimmed) > 24000:
        trimmed = trimmed[:24000] + "\n...(truncated)"
    return (
        "Here is the full pipeline output to synthesize:\n\n"
        f"{trimmed}\n\n"
        "Produce the report JSON now."
    )


class ReportGenerator:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        load_dotenv()
        self._llm = llm

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_llm(agent=AGENT_KEY)
        return self._llm

    @property
    def model(self) -> str:
        return self.llm.model

    def generate(
        self,
        *,
        feature_extraction: dict,
        patents: list[dict],
        prosecutor: dict,
        defender: dict,
        risk_matrix: dict,
        design: dict,
        images: list[dict] | None = None,
    ) -> FinalReport:
        product = feature_extraction.get("product", {}) or {}
        alternatives = design.get("alternatives", []) or []
        context = {
            "product": product,
            "features": [
                {"id": f.get("id"), "name": f.get("name"), "function": f.get("function")}
                for f in feature_extraction.get("features", []) or []
            ],
            "patents": [
                {k: p.get(k) for k in ("patent_number", "title", "abstract", "assignee")}
                for p in patents
            ],
            "prosecutor": prosecutor,
            "defender": defender,
            "risk_matrix": risk_matrix,
            "design_alternatives": alternatives,
        }

        narrative = self._narrative(context, risk_matrix, prosecutor, defender)

        return FinalReport(
            executive_summary=narrative.executive_summary,
            key_risks=narrative.key_risks,
            important_uncertainties=narrative.important_uncertainties,
            recommended_next_steps=narrative.recommended_next_steps,
            attorney_questions=narrative.attorney_questions,
            product_summary=product.get("summary", "") or product.get("name", ""),
            extracted_features=feature_extraction.get("features", []) or [],
            top_patents=patents,
            prosecutor_findings=prosecutor,
            defender_findings=defender,
            claim_mappings=prosecutor.get("claim_element_mappings", []) or [],
            risk_matrix=risk_matrix,
            design_alternatives=alternatives,
            redesign_concepts=images or [],
            legal_disclaimer=LEGAL_DISCLAIMER,
        )

    # -- narrative with a deterministic fallback -------------------------
    def _narrative(
        self, context: dict, risk_matrix: dict, prosecutor: dict, defender: dict
    ) -> ReportNarrative:
        try:
            return self.llm.complete_structured(
                [Message.system(SYSTEM_PROMPT), Message.user(_context_prompt(context))],
                ReportNarrative,
            )
        except LLMError:
            return _fallback_narrative(risk_matrix, prosecutor, defender)


def _fallback_narrative(
    risk_matrix: dict, prosecutor: dict, defender: dict
) -> ReportNarrative:
    overall = str(risk_matrix.get("overall_risk") or "unknown").lower()
    risks = risk_matrix.get("risks", []) or []
    high = [r for r in risks if str(r.get("risk_level", "")).lower() == "high"]
    mappings = prosecutor.get("claim_element_mappings", []) or []
    distinctions = defender.get("distinctions", []) or []

    key_risks = [
        f"{r.get('claim_element', 'A claim element')}: {r.get('reason', 'flagged by the risk matrix')}"
        for r in (high or risks)[:5]
    ] or ["No individual claim element was scored high risk on the supplied evidence."]

    return ReportNarrative(
        executive_summary=(
            f"The preliminary assessment rates overall prior-art exposure as "
            f"{overall}. The Prosecutor mapped {len(mappings)} product feature(s) "
            f"to patent claim elements; the Defender identified "
            f"{len(distinctions)} potential distinction(s). This is an "
            f"AI-assisted preliminary analysis, not a legal opinion."
        ),
        key_risks=key_risks,
        important_uncertainties=[
            "Claim scope and construction have not been reviewed by counsel.",
            "Patent validity and enforceability were not assessed.",
            "The patent search is not exhaustive and may miss relevant art.",
        ],
        recommended_next_steps=[
            "Have a patent attorney review the highest-risk claim elements.",
            "Evaluate the engineering design-around alternatives for feasibility.",
            "Commission a professional freedom-to-operate search before launch.",
        ],
        attorney_questions=[
            f"Does our product's '{m.get('product_feature', 'feature')}' fall within "
            f"the scope of claim element '{m.get('claim_element', '')}' of "
            f"{m.get('patent_id', 'the cited patent')}?"
            for m in mappings[:5]
        ]
        or [
            "Are there any patents in this space that a freedom-to-operate search "
            "should prioritize?"
        ],
    )


__all__ = ["ReportGenerator", "AGENT_KEY", "SYSTEM_PROMPT"]
