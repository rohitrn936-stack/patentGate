import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent4.models import DesignOutput


# Load the shared root .env (project root is two levels up from this module).
_ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT_DIR / ".env")

# Fallback model ID used when OPENAI_MODEL is unset (matches Agents 1 and 3).
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

MODEL_NAME = os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
You are the Design-Around Engi

neer, Agent 4 of the PatentGate system.

Your purpose is to receive:

1. Original product features (from Agent 1)
2. Prosecutor analysis of risky claim elements (from Agent 2)
3. Defender analysis of distinctions and weaknesses (from Agent 3)

Using all three inputs, you propose alternative engineering designs
that are intended to REDUCE overlap with the risky patent claim elements
identified by the Prosecutor.

You are an ENGINEERING and DESIGN assistant, NOT a legal assistant.

CRITICAL RULES:

- NEVER claim that a design is "patent safe".
- NEVER claim a design "guarantees no infringement".
- NEVER claim a design "avoids all patents".
- NEVER give legal advice or make legal conclusions.

Use cautious language such as:
- "designed to reduce overlap"
- "potentially reduces exposure"
- "changes the identified claim element"
- "requires legal review"

You must produce EXACTLY 3 alternative designs.

For each alternative:

1. "description" - A detailed engineering description of the modified design.
2. "avoids_claim_element" - The specific risky claim element this design changes
   or avoids.
3. "changes_from_original" - A list of strings describing how this design
   differs from the original product.
4. "tradeoff" - The engineering advantages and disadvantages of this change.
5. "why_it_differs" - Why this design differs from the identified patent claim
   element.
6. "risk_reduction_rationale" - How this change may reduce overlap with the
   identified claim element.
7. "design_generation_prompt" - A DALL-E-style prompt to generate an engineering
   concept image of this alternative design.

Return ONLY valid JSON with exactly these top-level fields:

{
    "agent": "design-engineer",
    "status": "completed",
    "alternatives": [ ... 3 items ... ],
    "legal_disclaimer": "..."
}

Do not invent product features or patent information that were not supplied.
Do not use information that was not supplied to you.
"""


def build_prompt(product, prosecutor, defender):
    return f"""
You are proposing alternative engineering designs.

ORIGINAL PRODUCT (from Agent 1):

{json.dumps(product, indent=2)}


PROSECUTOR ANALYSIS (from Agent 2):

{json.dumps(prosecutor, indent=2)}


DEFENDER ANALYSIS (from Agent 3):

{json.dumps(defender, indent=2)}


Propose exactly 3 alternative engineering designs intended to REDUCE overlap
with the risky claim elements identified by the Prosecutor, while taking into
account the distinctions and weaknesses identified by the Defender.

For each of the 3 alternatives, provide:

- "id": 1, 2, or 3
- "description"
- "avoids_claim_element"
- "changes_from_original" (a list of strings)
- "tradeoff"
- "why_it_differs"
- "risk_reduction_rationale"
- "design_generation_prompt" (a DALL-E-style image prompt)

Remember the strict rules:

- NEVER claim a design is "patent safe" or "guarantees no infringement".
- Use cautious language such as "designed to reduce overlap",
  "potentially reduces exposure", "changes the identified claim element",
  "requires legal review".

Return ONLY valid JSON.
"""


def generate_designs(product, prosecutor, defender):
    """
    Normal non-streaming generation.

    Returns:
        DesignOutput
    """

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=build_prompt(product, prosecutor, defender)
    )

    output_text = response.output_text

    result = DesignOutput.model_validate_json(output_text)

    return result


def stream_designs(product, prosecutor, defender):
    """
    Streaming generation.

    Yields:
        {"type": "token", "text": ...}
        {"type": "result", "data": {...}}
        {"type": "error", "error": ...}
    """

    stream = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=build_prompt(product, prosecutor, defender),
        stream=True
    )

    complete_text = ""

    for event in stream:

        if event.type == "response.output_text.delta":

            chunk = event.delta

            complete_text += chunk

            yield {
                "type": "token",
                "text": chunk
            }

    try:

        result = DesignOutput.model_validate_json(complete_text)

        yield {
            "type": "result",
            "data": result.model_dump()
        }

    except Exception as error:

        yield {
            "type": "error",
            "error": f"Could not parse final structured output: {str(error)}"
        }