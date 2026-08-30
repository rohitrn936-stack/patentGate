"""Agent 3 - Defender reasoning using the OpenAI API.

This module is responsible for the actual defense analysis: it takes Agent 2's
JSON (claim elements + prior-art information) and produces a structured
``DefenseAnalysis``. It uses the OpenAI Chat Completions API and never performs
a new patent search.

API key resolution (in order):
1. ``NVIDIA_API_KEY`` environment variable (loaded from ``.env``).
2. An explicit ``api_key`` passed to the constructor.

Model resolution:
1. ``OPENAI_MODEL`` environment variable.
2. An explicit ``model`` passed to the constructor.
3. ``DEFAULT_OPENAI_MODEL`` fallback.

The key is never hard-coded and never logged.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from .schemas import DefenseAnalysis

# Fallback OpenAI model used by Agent 3 when OPENAI_MODEL is unset.
DEFAULT_OPENAI_MODEL = "deepseek-ai/deepseek-v4-pro-0813"

# NVIDIA OpenAI-compatible endpoint.
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Redacts anything that looks like a credential so errors never leak secrets.
_SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]+|sk-proj-[A-Za-z0-9_-]+)")


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

# Prompt that asks the model to be tolerant of missing fields and still produce
# a best-effort analysis rather than failing.
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
    """Wraps the OpenAI API for Agent 3 defense analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        load_dotenv()
        self._api_key = (api_key or "").strip()
        self._model = (model or "").strip()

        if not self._api_key:
            import os

            self._api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
        if not self._model:
            import os

            self._model = (os.getenv("OPENAI_MODEL") or "").strip() or DEFAULT_OPENAI_MODEL

        if not self._api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is empty or missing. Add it to your .env file "
                "or the agent3/.env file and try again."
            )

        self._client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=self._api_key,
        )

    def _complete_json(self, payload: dict) -> dict:
        """Send the Agent 2 payload to OpenAI and return parsed JSON."""
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": ANALYZE_TEMPLATE.format(
                            payload=json.dumps(payload, indent=2, ensure_ascii=False)
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI API call failed: {_mask(str(exc))}") from exc

        text = (completion.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("OpenAI returned an empty response.")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI returned invalid JSON.") from exc

    def analyze(self, agent2_output: dict) -> DefenseAnalysis:
        """Run the defense analysis over Agent 2's output."""
        data = self._complete_json(agent2_output)
        try:
            return DefenseAnalysis.model_validate(data)
        except Exception as exc:
            raise ValueError(
                "OpenAI defense analysis did not match the expected schema."
            ) from exc


__all__ = ["Defender", "DEFAULT_OPENAI_MODEL"]