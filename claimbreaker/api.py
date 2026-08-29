"""Minimal Agent 1 HTTP endpoint for local integration testing."""
from __future__ import annotations
from typing import Annotated
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from .feature_extractor import extract_features_from_image_bytes
from .models import FeatureExtractionResult

app = FastAPI(title="ClaimBreaker Agent 1", version="0.1.0")

@app.post("/agent-1/extract", response_model=FeatureExtractionResult)
async def extract_product_features(product_description: Annotated[str, Form(...)], image: Annotated[UploadFile | None, File()] = None) -> FeatureExtractionResult:
    """Accept multipart form data with a description and optional JPEG/PNG/WebP."""
    try:
        return extract_features_from_image_bytes(product_description, await image.read() if image else None, image.content_type if image else None)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
