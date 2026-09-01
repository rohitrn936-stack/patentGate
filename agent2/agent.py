"""Agent 2 - Prosecutor (adversarial patent analysis).

Runs through the provider-agnostic :mod:`llm` layer. The Prosecutor argues that
retrieved patents' claim elements *could potentially* read on the product; it
never states that infringement exists and never invents patent data.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Optional

from dotenv import load_dotenv

from llm import LLMError, Message, get_llm
from llm.base import LLMProvider

from .schemas import ProsecutorOutput

AGENT_KEY = "agent2"

SYSTEM_PROMPT = """You are the Prosecutor, also known as Adversarial Analyst A.

Your purpose is to argue the case that retrieved patents could potentially read
on the user's product.

You receive:
1. Product feature information
2. Patent summaries
3. Patent claims

Your responsibilities:
1. Analyze every supplied patent.
2. Examine the claims of each patent.
3. Break claims into individual claim elements.
4. Compare each claim element with product features.
5. Identify product features that correspond to claim elements.
6. Identify potentially risky claims.
7. Assign a confidence score from 0 to 1 for every patent.

You are the PROSECUTOR. Actively look for evidence supporting potential overlap.

IMPORTANT:
- Do NOT give legal advice.
- Do NOT state that infringement definitely exists.
- Do NOT state that a patent definitely covers the product.
- Do NOT invent product features or patent information.
- Do NOT use information that was not supplied.
- Do NOT treat the analysis as a legal conclusion.

Use cautious language such as "potentially overlaps", "appears to correspond",
"could read on", "based on the supplied information".

Confidence represents confidence in the claim-to-product mapping. It does NOT
represent probability of legal infringement.

Return ONLY valid JSON with exactly these top-level fields:
{
    "risk_claims": [
        {"patent_id": "", "claim_id": "", "risk_level": "", "reason": ""}
    ],
    "claim_element_mappings": [
        {"patent_id": "", "claim_id": "", "claim_element": "",
         "product_feature": "", "strength": "", "explanation": ""}
    ],
    "confidence_per_patent": [
        {"patent_id": "", "confidence": 0.0, "explanation": ""}
    ]
}"""


def _build_user_prompt(product: dict, patents: list[dict]) -> str:
    return (
        "Analyze the product against all supplied patents.\n\n"
        f"PRODUCT:\n{json.dumps(product, indent=2)}\n\n"
        f"PATENTS:\n{json.dumps(patents, indent=2)}\n\n"
        "For every patent: examine its claims, break them into elements, map "
        "elements to product features where appropriate, identify potentially "
        "risky claims, explain the reasoning, and assign a confidence score "
        "between 0 and 1. Do not invent missing information. Do not make a "
        "definitive legal determination. Return JSON only."
    )


class Prosecutor:
    """Agent 2 analysis, provider-agnostic."""

    def __init__(self, llm: Optional[LLMProvider] = None) -> None:
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

    def analyze(self, product: dict, patents: list[dict]) -> ProsecutorOutput:
        messages = [
            Message.system(SYSTEM_PROMPT),
            Message.user(_build_user_prompt(product, patents)),
        ]
        llm = self.llm
        try:
            return llm.complete_structured(messages, ProsecutorOutput)
        except LLMError as exc:
            raise RuntimeError(f"Prosecutor LLM call failed: {exc}") from exc

    def stream(self, product: dict, patents: list[dict]) -> Iterator[dict]:
        """Yield ``{"type": "token"|"result"|"error", ...}`` events."""
        messages = [
            Message.system(SYSTEM_PROMPT),
            Message.user(_build_user_prompt(product, patents)),
        ]
        buffer = ""
        try:
            for event in self.llm.stream(messages):
                if event.type == "text" and event.text:
                    buffer += event.text
                    yield {"type": "token", "text": event.text}
        except LLMError as exc:
            yield {"type": "error", "error": f"Prosecutor LLM stream failed: {exc}"}
            return

        try:
            result = self.llm._parse_structured(buffer, ProsecutorOutput)
            yield {"type": "result", "data": result.model_dump()}
        except LLMError as exc:
            yield {"type": "error", "error": f"Could not parse final structured output: {exc}"}


__all__ = ["Prosecutor", "AGENT_KEY", "SYSTEM_PROMPT"]
