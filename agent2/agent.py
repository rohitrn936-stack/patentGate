import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent2.models import ProsecutorOutput


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
You are the Prosecutor, also known as Adversarial Analyst A.

Your purpose is to argue the case that retrieved patents could
potentially read on the user's product.

You receive:

1. Product feature information
2. Patent summaries
3. Patent claims

Your responsibilities are:

1. Analyze every supplied patent.
2. Examine the claims of each patent.
3. Break claims into individual claim elements.
4. Compare each claim element with product features.
5. Identify product features that correspond to claim elements.
6. Identify potentially risky claims.
7. Assign a confidence score from 0 to 1 for every patent.

You are the PROSECUTOR.

Actively look for evidence supporting potential overlap.

IMPORTANT:

- Do NOT give legal advice.
- Do NOT state that infringement definitely exists.
- Do NOT state that a patent definitely covers the product.
- Do NOT invent product features.
- Do NOT invent patent information.
- Do NOT use information that was not supplied.
- Do NOT treat the analysis as a legal conclusion.

Use cautious language such as:

"potentially overlaps"
"appears to correspond"
"could read on"
"based on the supplied information"

Confidence represents confidence in the claim-to-product mapping.

It does NOT represent probability of legal infringement.

Return ONLY valid JSON for the final analysis.
"""


def build_prompt(product, patents):

    return f"""
Analyze the product against all five supplied patents.

PRODUCT:

{json.dumps(product, indent=2)}


PATENTS:

{json.dumps(patents, indent=2)}


For every patent:

1. Examine its claims.
2. Break claims into individual elements.
3. Map claim elements to product features where appropriate.
4. Identify potentially risky claims.
5. Explain the reasoning behind each mapping.
6. Assign a confidence score between 0 and 1.

Look specifically for evidence that the supplied product features
could correspond to elements of the supplied patent claims.

Do not invent missing information.

Do not make a definitive legal determination.

Return JSON with exactly these top-level fields:

{{
    "risk_claims": [],
    "claim_element_mappings": [],
    "confidence_per_patent": []
}}

Each risk_claim must contain:

- patent_id
- claim_id
- risk_level
- reason

Each claim_element_mapping must contain:

- patent_id
- claim_id
- claim_element
- product_feature
- strength
- explanation

Each confidence_per_patent must contain:

- patent_id
- confidence
- explanation
"""


def analyze_product(product, patents):
    """
    Normal non-streaming analysis.
    """

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=build_prompt(product, patents)
    )

    output_text = response.output_text

    result = ProsecutorOutput.model_validate_json(
        output_text
    )

    return result


def stream_analysis(product, patents):
    """
    Streaming analysis.

    Returns:

        text_chunks
        final structured result
    """

    stream = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=build_prompt(product, patents),
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

    # Parse the complete JSON after streaming finishes.
    try:

        result = ProsecutorOutput.model_validate_json(
            complete_text
        )

        yield {
            "type": "result",
            "data": result.model_dump()
        }

    except Exception as error:

        yield {
            "type": "error",
            "error": f"Could not parse final structured output: {str(error)}"
        }