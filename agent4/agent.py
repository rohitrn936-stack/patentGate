"""Agent 4 - Design-Around Engineer, provider-agnostic.

Takes Agent 1 (product), Agent 2 (prosecutor) and Agent 3 (defender) outputs and
proposes alternative engineering designs that aim to REDUCE overlap with the
risky claim elements. Engineering guidance only - never a legal conclusion.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from dotenv import load_dotenv

from llm import LLMError, Message, get_llm
from llm.base import LLMProvider

from .models import DesignOutput

AGENT_KEY = "agent4"

SYSTEM_PROMPT = """You are the Design-Around Engineer, Agent 4 of the PatentGate system.

You receive:
1. Original product features (from Agent 1)
2. Prosecutor analysis of risky claim elements (from Agent 2)
3. Defender analysis of distinctions and weaknesses (from Agent 3)

Using all three inputs, you propose alternative engineering designs intended to
REDUCE overlap with the risky patent claim elements identified by the
Prosecutor.

You are an ENGINEERING and DESIGN assistant, NOT a legal assistant.

CRITICAL RULES:
- NEVER claim that a design is "patent safe".
- NEVER claim a design "guarantees no infringement".
- NEVER claim a design "avoids all patents".
- NEVER give legal advice or make legal conclusions.

Use cautious language such as "designed to reduce overlap", "potentially reduces
exposure", "changes the identified claim element", "requires legal review".

You must produce EXACTLY 3 alternative designs. For each alternative provide:
1. "id": 1, 2, or 3
2. "description" - detailed engineering description of the modified design
3. "avoids_claim_element" - the specific risky claim element this design changes
4. "changes_from_original" - a list of strings
5. "tradeoff" - engineering advantages and disadvantages
6. "why_it_differs" - why this design differs from the identified claim element
7. "risk_reduction_rationale" - how this change may reduce overlap
8. "design_generation_prompt" - a DALL-E-style prompt for a concept image

Return ONLY valid JSON with exactly these top-level fields:
{
    "agent": "design-engineer",
    "status": "completed",
    "alternatives": [ ... 3 items ... ],
    "legal_disclaimer": "..."
}

Do not invent product features or patent information that were not supplied."""


def _build_user_prompt(product: dict, prosecutor: dict, defender: dict) -> str:
    return (
        "You are proposing alternative engineering designs.\n\n"
        f"ORIGINAL PRODUCT (from Agent 1):\n{json.dumps(product, indent=2)}\n\n"
        f"PROSECUTOR ANALYSIS (from Agent 2):\n{json.dumps(prosecutor, indent=2)}\n\n"
        f"DEFENDER ANALYSIS (from Agent 3):\n{json.dumps(defender, indent=2)}\n\n"
        "Propose exactly 3 alternative engineering designs intended to REDUCE "
        "overlap with the risky claim elements identified by the Prosecutor, "
        "while taking into account the distinctions and weaknesses identified by "
        "the Defender. Return ONLY valid JSON."
    )


class DesignEngineer:
    """Agent 4 generation, provider-agnostic."""

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

    def generate(self, product: dict, prosecutor: dict, defender: dict) -> DesignOutput:
        messages = [
            Message.system(SYSTEM_PROMPT),
            Message.user(_build_user_prompt(product, prosecutor, defender)),
        ]
        llm = self.llm
        try:
            return llm.complete_structured(messages, DesignOutput)
        except LLMError as exc:
            raise RuntimeError(f"Design engineer LLM call failed: {exc}") from exc

    def stream(self, product: dict, prosecutor: dict, defender: dict) -> Iterator[dict]:
        messages = [
            Message.system(SYSTEM_PROMPT),
            Message.user(_build_user_prompt(product, prosecutor, defender)),
        ]
        buffer = ""
        try:
            for event in self.llm.stream(messages):
                if event.type == "text" and event.text:
                    buffer += event.text
                    yield {"type": "token", "text": event.text}
        except LLMError as exc:
            yield {"type": "error", "error": f"Design engineer stream failed: {exc}"}
            return
        try:
            result = self.llm._parse_structured(buffer, DesignOutput)
            yield {"type": "result", "data": result.model_dump()}
        except LLMError as exc:
            yield {"type": "error", "error": f"Could not parse final structured output: {exc}"}


__all__ = ["DesignEngineer", "AGENT_KEY", "SYSTEM_PROMPT"]
