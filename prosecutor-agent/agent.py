import json
import os
from typing import Any, Dict, Generator, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.7-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Create a .env file and add GEMINI_API_KEY=your_key"
    )

# Gemini provides an OpenAI-compatible API.
client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


SYSTEM_PROMPT = """
You are Agent 2 — Prosecutor Agent in the PatentGate system.

Your job is to perform adversarial patent infringement analysis.

You receive:
1. A product description and its features.
2. A list of relevant patents and their claims.

Your job is to identify claim elements that could potentially be read
onto the product.

You are NOT a lawyer and must NOT claim that infringement has been
legally established.

You must return structured JSON.

Focus on:
- Product features
- Patent claim elements
- Potential overlap
- Risk level
- Explanation
- Evidence from the supplied patent information

Return JSON in this format:

{
    "agent": "prosecutor",
    "risk_level": "high | medium | low",
    "summary": "short explanation",
    "claim_elements": [
        {
            "claim_element": "patent claim element",
            "product_feature": "corresponding product feature",
            "overlap": true,
            "risk": "high | medium | low",
            "reason": "why this could overlap"
        }
    ],
    "patents_analyzed": [],
    "disclaimer": "This is an AI-generated preliminary analysis and is not legal advice."
}

Do not invent patent information.
Only use information supplied in the request.
"""


def _build_messages(
    product: Dict[str, Any],
    patents: List[Dict[str, Any]],
) -> List[Dict[str, str]]:

    user_prompt = f"""
Analyze the following product against the supplied patents.

PRODUCT:
{json.dumps(product, indent=2)}

PATENTS:
{json.dumps(patents, indent=2)}

Return ONLY valid JSON.
Do not use markdown.
Do not wrap the JSON in ```json blocks.
"""

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def _parse_result(text: str) -> Dict[str, Any]:

    text = text.strip()

    # Remove accidental markdown fences if Gemini returns them.
    if text.startswith("```json"):
        text = text[7:]

    if text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        return {
            "agent": "prosecutor",
            "risk_level": "unknown",
            "summary": text,
            "claim_elements": [],
            "patents_analyzed": [],
            "disclaimer": (
                "This is an AI-generated preliminary analysis "
                "and is not legal advice."
            ),
        }


def analyze_product(
    product: Dict[str, Any],
    patents: List[Dict[str, Any]],
) -> Dict[str, Any]:

    messages = _build_messages(product, patents)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        response_format={
            "type": "json_object"
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("Gemini returned an empty response.")

    return _parse_result(content)


def stream_analysis(
    product: Dict[str, Any],
    patents: List[Dict[str, Any]],
) -> Generator[Dict[str, Any], None, None]:

    messages = _build_messages(product, patents)

    try:

        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            stream=True,
        )

        full_text = ""

        for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            text = delta.content

            if text:
                full_text += text

                yield {
                    "type": "token",
                    "text": text,
                }

        result = _parse_result(full_text)

        yield {
            "type": "result",
            "data": result,
        }

    except Exception as error:

        yield {
            "type": "error",
            "error": str(error),
        }