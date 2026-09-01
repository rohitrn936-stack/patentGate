"""Agent 3 - Defender reasoning through the provider-agnostic LLM layer.

Takes Agent 2's JSON (claim elements + prior-art information) and produces a
structured :class:`DefenseAnalysis`. The model provider (OpenAI / Anthropic /
Gemini / OpenRouter / local) is selected by environment config - see
:mod:`llm.config`. Agent 3 never performs a new patent search.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from dotenv import load_dotenv

from llm import LLMError, Message, get_llm
from llm.base import LLMProvider

from .schemas import DefenseAnalysis

#: Agent key for provider config (``AGENT3_LLM_*`` env overrides).
AGENT_KEY = "agent3"

# Redacts anything that looks like a credential so errors never leak secrets.
_SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]{10,}|sk-proj-[A-Za-z0-9_-]{10,}|nvapi-[A-Za-z0-9_-]{10,})")


SYSTEM_PROMPT = """You are the "Defender" agent in a multi-agent patent analysis \
system. Your role is to defend an invention by critically examining its claimed \
elements against prior-art information supplied by an upstream "Prosecutor" \
agent.

You receive structured input describing:
- claim_elements: the technical elements being claimed for the invention;
- prior_art: the prior-art concepts/references the Prosecutor identified;
- prior_art_concepts / similar_known_concepts: any similar known concepts (if
  present).

Produce a defense analysis with these goals:
1. Identify distinctions - where the claimed invention differs from the prior
   art.
2. Identify prior-art gaps - areas the prior art appears NOT to cover.
3. Identify weak claim elements - elements that appear broad, generic, or
   likely to be challenged by prior art.

Rules you MUST follow:
- You do NOT perform a new patent search. You only reason over the supplied
  prior-art information.
- Never fabricate patent numbers, publication numbers, URLs, filing dates, or
  citations.
- Never claim that a specific real patent was or was not found.
- Never state that an invention is or is not legally patentable, and never
  state that it does or does not infringe a patent.
- Never present output as legal advice.
- risk must be exactly one of "low", "medium", or "high".
- confidence must be a number from 0.0 to 1.0.
- Explain the reasoning behind every finding.

Return ONLY valid JSON matching this exact shape, with no commentary:
{
  "distinctions": [
    {"claim_element": "", "distinction": "", "reasoning": ""}
  ],
  "prior_art_gaps": [
    {"claim_element": "", "gap": "", "reasoning": ""}
  ],
  "weak_claim_elements": [
    {"claim_element": "", "reasoning": "", "risk": "medium"}
  ],
  "overall_assessment": "",
  "confidence": 0.0,
  "disclaimer": "This is an AI-based analysis and is NOT a verified patent search or legal opinion."
}"""

ANALYZE_TEMPLATE = """Here is the input from Agent 2 (the Prosecutor):

{payload}

Note: some fields above may be missing or empty. If claim elements are absent,
describe the invention from whatever description is available. If prior art is
absent, state that no prior-art information was supplied and mark any specific
distinction as uncertain.

Produce the defense analysis JSON now."""


def _mask(text: str) -> str:
    return _SECRET_PATTERN.sub("[REDACTED KEY]", text)


class Defender:
    """Runs Agent 3's defense analysis through the provider-agnostic layer."""

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

    def analyze(self, agent2_output: dict) -> DefenseAnalysis:
        """Run the defense analysis over Agent 2's output."""
        user = ANALYZE_TEMPLATE.format(
            payload=json.dumps(agent2_output, indent=2, ensure_ascii=False)
        )
        # Provider resolution errors (missing key, unknown provider) surface
        # unmasked so the operator can act on them.
        llm = self.llm
        try:
            return llm.complete_structured(
                [Message.system(SYSTEM_PROMPT), Message.user(user)],
                DefenseAnalysis,
            )
        except LLMError as exc:
            raise RuntimeError(f"LLM call failed: {_mask(str(exc))}") from exc


__all__ = ["Defender", "AGENT_KEY"]
