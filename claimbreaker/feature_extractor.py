"""Agent 1: OpenAI-powered technical feature extraction, without patent search."""
from __future__ import annotations
import base64, mimetypes, os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from pydantic import ValidationError
from .models import FeatureExtractionResult

load_dotenv()
DEFAULT_MODEL = "gpt-5-nano"
SUPPORTED_IMAGE_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
SYSTEM_INSTRUCTIONS = """You are ClaimBreaker Agent 1, a technical feature extraction agent. Extract a precise, structured technical representation of the supplied product description and optional product image for a later Patent Search Layer.

Focus on engineering functionality, not marketing language. Break the product into atomic technical features: sensors, controllers, processors, communication modules, mechanical structures, energy sources, data processing, control mechanisms, physical relationships, input/output behavior, and detection mechanisms.

Set evidence_type exactly as follows: explicit for directly stated description facts; inferred for cautious, reasonable technical inferences from stated facts; visual for facts observed only in the image. Do not invent components, specifications, protocols, materials, or behavior. List absent or ambiguous details in uncertainties. Features must be atomic rather than marketing labels. Relationships must use feature IDs only, in the form 'F1 -> F2'. Generate concise patent-search terms and technical keywords or synonyms grounded in the provided evidence.

You are not a legal agent. Do not search patents, identify patents, assess novelty, patentability, infringement, legal risk, or provide legal advice. Do not claim that any patent covers the product. Only return the structured technical extraction."""

def extract_features(product_description: str, image_path: str | None = None) -> FeatureExtractionResult:
    """Return a validated result using ``OPENAI_API_KEY`` and GPT-5 nano."""
    image_bytes = None
    media_type = None
    if image_path:
        path = Path(image_path)
        if not path.is_file(): raise FileNotFoundError(f"Image file not found: {path}")
        image_bytes, media_type = path.read_bytes(), _image_media_type(path.name)
    return extract_features_from_image_bytes(product_description, image_bytes, media_type)

def extract_features_from_image_bytes(product_description: str, image_bytes: bytes | None = None, media_type: str | None = None, *, client: Any | None = None) -> FeatureExtractionResult:
    """Return structured features from text and optional JPEG, PNG, or WebP bytes."""
    description = _validated_description(product_description)
    if image_bytes is not None:
        if not image_bytes: raise ValueError("image_bytes must not be empty")
        if media_type not in SUPPORTED_IMAGE_MEDIA_TYPES: raise ValueError("image must be JPEG, PNG, or WebP")
    response = (client or _default_client()).responses.parse(
        model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        instructions=SYSTEM_INSTRUCTIONS,
        input=[{"role": "user", "content": _user_content(description, image_bytes, media_type)}],
        text_format=FeatureExtractionResult,
    )
    parsed = getattr(response, "output_parsed", None)
    if parsed is None: raise ValueError("OpenAI did not return a structured Agent 1 response")
    return _validate_payload(parsed)

def _default_client() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: raise RuntimeError("OPENAI_API_KEY is required to run Agent 1")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install Agent 1 dependencies: pip install -e .") from exc
    return OpenAI(api_key=api_key)

def _validated_description(value: str) -> str:
    if not isinstance(value, str) or not (description := value.strip()): raise ValueError("product_description must be a non-empty string")
    return description

def _image_media_type(filename: str) -> str:
    media_type, _ = mimetypes.guess_type(filename)
    if media_type == "image/jpg": media_type = "image/jpeg"
    if media_type not in SUPPORTED_IMAGE_MEDIA_TYPES: raise ValueError("image_path must be a JPEG, PNG, or WebP file")
    return media_type

def _user_content(description: str, image_bytes: bytes | None, media_type: str | None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": f"Product description:\n{description}"}]
    if image_bytes is not None and media_type is not None:
        data_url = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        content.append({"type": "input_image", "image_url": data_url})
    return content

def _validate_payload(payload: Any) -> FeatureExtractionResult:
    try: return FeatureExtractionResult.model_validate(payload)
    except ValidationError as exc: raise ValueError(f"OpenAI returned an invalid Agent 1 payload: {exc}") from exc
