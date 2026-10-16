"""Agent 1 - technical feature extraction and knowledge analysis.

The two jobs (feature extraction, similar-concept analysis) run through the
provider-agnostic :mod:`llm` layer, so the underlying model can be OpenAI,
Anthropic, Gemini, OpenRouter or a local server without any change here. There
is still no external search, web scraping, or patent database access.
"""

from __future__ import annotations

import base64
import os

from llm import ImagePart, LLMError, Message, TextPart, get_llm
from llm.base import LLMProvider

from .schemas import FeatureExtraction, KnowledgeAnalysis

#: Agent key used to resolve provider config (``AGENT1_LLM_*`` env overrides).
AGENT_KEY = "agent1"

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
IMAGE_MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

SYSTEM_FEATURE_EXTRACTION = """You are a technical product analyst for a prior-art patent research tool.

The user has NOT asked for a legal opinion. Never make a legal conclusion and
never state that a product infringes, does not infringe, or is covered by a
patent. Do not use legal terms such as "infringement", "claim coverage", or
"validity".

Given a product description and an optional product image, extract technically
meaningful information. Do NOT invent technical specifications (voltages,
materials, dimensions, capacities, radio bands, ...) unless they are actually
stated in the description or visible in the image.

For EVERY feature set:
- id: a short identifier such as "F1", "F2", ...
- name: short feature name
- description: what the feature is
- component: which component it belongs to (use the component names below)
- function: what it does
- evidence: quote/summary of what in the user's input or image supports it
- evidence_source: one of
    "user_stated"      -> explicitly stated in the product description
    "image_observation"-> a technical characteristic actually visible in the
                          image (only list what is visible; never guess the
                          internal mechanism)
    "assumption"       -> a reasonable engineering assumption
- confidence: a number between 0.0 and 1.0. Use 1.0 for explicit user facts,
  lower values for image observations, and the lowest values for assumptions.
  Any assumption must also be listed under "assumptions".

Also extract:
- product: name and a one-paragraph technical summary
- components: the physical/logical building blocks (id, name, description,
  function)
- technical_concepts: broader technical areas the product relies on
- mechanisms: working principles
- materials: materials only when stated or visible
- interfaces: communication/electrical interfaces (Bluetooth, USB, I2C, ...)
- software_features: software-related technical behavior
- assumptions: list every assumption explicitly with a reason

Ignore marketing/design-fluff that has no technical meaning.

Return ONLY valid JSON, no commentary, matching this exact shape:
{
  "product": {"name": "", "summary": ""},
  "components": [{"id": "C1", "name": "", "description": "", "function": ""}],
  "features": [
    {
      "id": "F1", "name": "", "description": "", "component": "", "function": "",
      "evidence": "", "evidence_source": "user_stated", "confidence": 1.0
    }
  ],
  "technical_concepts": [{"name": "", "description": ""}],
  "mechanisms": [{"name": "", "description": "", "purpose": ""}],
  "materials": [{"name": "", "purpose": ""}],
  "interfaces": [{"name": "", "interface_type": "", "protocol": "", "description": ""}],
  "software_features": [{"name": "", "description": ""}],
  "assumptions": [{"message": "", "reason": ""}]
}"""

SYSTEM_KNOWLEDGE_ANALYSIS = """You are a technical analyst helping identify
potentially related prior-art concepts for a product invention.

IMPORTANT: You have NO access to the web, patent databases, or any external
search. You must rely ONLY on knowledge you have already learned during
training.

You must NOT fabricate any patent identifiers: no publication numbers, patent
numbers, patent URLs, filing dates, or legal-status information.

You must NOT claim that a real, specific patent was found. Instead, describe
results as "similar known concepts" or "potentially similar prior-art
concepts".

Given an invention description and its extracted technical features, produce an
analysis with this exact JSON shape:
{
  "invention": "<short summary of the invention>",
  "technical_features": ["<feature 1>", "<feature 2>", ...],
  "similar_known_concepts": [
    {
      "name": "<concept / technology name>",
      "why_similar": "<why it is similar to the invention>",
      "matching_features": ["<which features match>"],
      "differences": "<how it differs from the invention>",
      "similarity_score": 0.0
    }
  ],
  "similarity_score": 0.0,
  "similarity_explanation": "<overall explanation of the similarity>",
  "potentially_overlapping_areas": ["<domain or area likely to overlap>"],
  "confidence": 0.0,
  "disclaimer": "This analysis is based on the model's learned knowledge and is NOT a verified patent search."
}

Rules:
- similarity_score (both per-concept and overall) is a number from 0.0 (no
  similarity) to 1.0 (near-identical).
- confidence expresses how sure you are of the analysis, from 0.0 to 1.0.
- Only describe concepts and technologies you genuinely know about.
- Never cite a specific patent number, publication number, or URL.
- The disclaimer must explicitly state the analysis is based on learned
  knowledge and is NOT a verified patent search.

Return ONLY valid JSON, no commentary."""


def load_image_as_data_url(image_path: str) -> str:
    """Read an image file and return it as a base64 data URL.

    Raises FileNotFoundError if the path does not exist and ValueError for
    unsupported image types.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    extension = os.path.splitext(image_path)[1].lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image type '{extension}'. Supported: "
            + ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
            + " (PNG and JPEG)."
        )

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")

    return f"data:{IMAGE_MIME_TYPES[extension]};base64,{encoded}"


class FeatureExtractor:
    """Runs Agent 1's two LLM jobs through the provider-agnostic layer."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        # Resolve lazily so importing this module never needs credentials.
        self._llm = llm

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_llm(agent=AGENT_KEY)
        return self._llm

    @property
    def model(self) -> str:
        return self.llm.model

    def extract_features(
        self,
        product_description: str,
        image_data_url: str | None = None,
    ) -> FeatureExtraction:
        """Job 1: analyze the description (+ optional image) for features."""
        user_text = f"PRODUCT DESCRIPTION:\n{product_description}"
        if image_data_url:
            user_text += (
                "\n\nAdditionally analyze the technical characteristics that "
                "are actually visible in the attached product image. Mark "
                "their evidence_source as image_observation."
            )
            content: list = [TextPart(text=user_text), ImagePart(url=image_data_url, detail="high")]
        else:
            content = user_text

        try:
            return self.llm.complete_structured(
                [Message.system(SYSTEM_FEATURE_EXTRACTION), Message.user(content)],
                FeatureExtraction,
            )
        except LLMError as exc:
            raise ValueError(f"Feature extraction failed: {exc}") from exc

    def analyze_similar_concepts(
        self,
        extraction: FeatureExtraction,
        product_description: str,
    ) -> KnowledgeAnalysis:
        """Job 2: analyze the model's learned knowledge for similar concepts."""
        feature_lines = "\n".join(
            f"- {f.name}: {f.description} (function: {f.function})"
            for f in extraction.features
        )
        user_text = (
            f"INVENTION DESCRIPTION:\n{product_description}\n"
            f"PRODUCT: {extraction.product.name} - {extraction.product.summary}\n"
            f"TECHNICAL FEATURES:\n{feature_lines}"
        )

        try:
            return self.llm.complete_structured(
                [Message.system(SYSTEM_KNOWLEDGE_ANALYSIS), Message.user(user_text)],
                KnowledgeAnalysis,
            )
        except LLMError as exc:
            raise ValueError(f"Knowledge analysis failed: {exc}") from exc


__all__ = [
    "FeatureExtractor",
    "load_image_as_data_url",
    "SUPPORTED_IMAGE_EXTENSIONS",
    "AGENT_KEY",
]
