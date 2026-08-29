"""Agent 1 - orchestrator.

Runs the full Agent 1 pipeline:

    user description (+ optional image)
      -> OpenAI feature extraction
      -> OpenAI knowledge-based similar-concept analysis
      -> combined, validated Agent1Output (JSON contract)

The similar-concept analysis is based ONLY on the model's learned knowledge;
there is no web search, no Gemini, and no external patent retrieval.

If the analysis step fails, Agent 1 still returns the successfully extracted
product features with ``status="analysis_failed"`` and an explanatory error,
rather than crashing.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from dotenv import load_dotenv

from .extractor import FeatureExtractor, load_image_as_data_url
from .schemas import Agent1Output, KnowledgeAnalysis

# Sensible default. Override via OPENAI_MODEL in .env.
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# Redacts anything that looks like an API key so errors never leak secrets.
_SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]{15,})")


def mask_secrets(text: str) -> str:
    """Replace secret-looking substrings so they are never printed."""
    return _SECRET_PATTERN.sub("[REDACTED KEY]", text)


def _env(name: str) -> str:
    """Read a required environment variable or raise a clear error."""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Add it to your .env file and try again."
        )
    return value


def _optional_env(name: str, default: str) -> str:
    """Read an optional environment variable with a fallback default."""
    return (os.getenv(name) or "").strip() or default


def run_agent1(
    description: str,
    image_path: Optional[str] = None,
    extractor: Optional[FeatureExtractor] = None,
    load_env: bool = True,
) -> Agent1Output:
    """Run the complete Agent 1 pipeline and return a validated output.

    ``extractor`` may be injected (e.g. in tests) to avoid creating a real
    API client.
    """
    if load_env:
        load_dotenv()

    description = (description or "").strip()
    if not description:
        raise ValueError("Product description is empty. Provide some text first.")

    # Load the optional image up front so we fail fast on bad paths.
    image_data_url = None
    if image_path:
        image_data_url = load_image_as_data_url(image_path)

    # Create the OpenAI backend unless it was injected.
    if extractor is None:
        extractor = FeatureExtractor(
            api_key=_env("OPENAI_API_KEY"),
            model=_optional_env("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        )

    # Job 1: technical feature extraction (OpenAI).
    extraction = extractor.extract_features(description, image_data_url=image_data_url)

    # Job 2: knowledge-based similar-concept analysis (OpenAI).
    errors: list[str] = []
    status = "ok"
    analysis = KnowledgeAnalysis()
    try:
        analysis = extractor.analyze_similar_concepts(extraction, description)
    except Exception as exc:
        status = "analysis_failed"
        errors.append(
            f"Similar-concept analysis failed: {type(exc).__name__}: "
            f"{mask_secrets(str(exc))}"
        )

    output = Agent1Output(
        status=status,
        errors=errors,
        product=extraction.product,
        components=extraction.components,
        features=extraction.features,
        technical_concepts=extraction.technical_concepts,
        mechanisms=extraction.mechanisms,
        materials=extraction.materials,
        interfaces=extraction.interfaces,
        software_features=extraction.software_features,
        assumptions=extraction.assumptions,
        analysis=analysis,
    )
    return validate_output(output)


def validate_output(output: Agent1Output) -> Agent1Output:
    """Final validation step: round-trip through JSON against the schema."""
    return Agent1Output.model_validate_json(output.model_dump_json())


__all__ = [
    "run_agent1",
    "validate_output",
    "mask_secrets",
    "FeatureExtractor",
    "Agent1Output",
]