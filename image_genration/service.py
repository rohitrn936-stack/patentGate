"""Before/After engineering concept image generation for Agent 4 redesigns.

Configuration is resolved through :func:`llm.config.resolve_llm_config` with the
``image`` agent key, so it honours the same environment scheme as every other
agent::

    IMAGE_LLM_PROVIDER=openai        # or openrouter / gemini / local
    IMAGE_LLM_MODEL=gpt-image-1
    IMAGE_LLM_API_KEY=...            # falls back to OPENAI_API_KEY
    IMAGE_LLM_BASE_URL=...           # optional, for compatible endpoints

Image generation is an inherently different modality from chat, so this uses the
OpenAI Images API surface directly (which OpenRouter, Gemini's compatibility
layer and local servers such as LM Studio also expose). Providers without image
support raise a clear configuration error.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from llm.config import resolve_llm_config
from llm.errors import LLMConfigError

from .prompts import build_before_after_prompt
from .schemas import GeneratedImage, ImageGenerationRequest, ImageGenerationResponse

load_dotenv()

_IMAGE_CAPABLE_PROVIDERS = {"openai", "openrouter", "gemini", "local"}
_DEFAULT_IMAGE_MODEL = "gpt-image-1"


class ImageGenerationService:
    """Generates one Before/After image per Agent 4 redesign option."""

    def __init__(
        self,
        *,
        output_dir: Optional[str] = None,
        config=None,
    ) -> None:
        self._config = config or resolve_llm_config(agent="image")
        self.output_dir = Path(output_dir or "generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider(self) -> str:
        return self._config.provider

    @property
    def model(self) -> str:
        return self._config.model or _DEFAULT_IMAGE_MODEL

    def _validate_configuration(self) -> None:
        if self._config.provider not in _IMAGE_CAPABLE_PROVIDERS:
            raise LLMConfigError(
                f"provider '{self._config.provider}' has no image generation; set "
                f"IMAGE_LLM_PROVIDER to one of {sorted(_IMAGE_CAPABLE_PROVIDERS)}",
                provider=self._config.provider,
            )
        if self._config.provider != "local" and not self._config.api_key:
            raise LLMConfigError(
                "no API key configured for image generation; set IMAGE_LLM_API_KEY "
                "or OPENAI_API_KEY",
                provider=self._config.provider,
            )

    def _client(self):
        from openai import OpenAI

        kwargs = {"api_key": self._config.api_key or "not-needed"}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        return OpenAI(**kwargs)

    def _save_base64_image(self, image_data: str, option_id: int) -> str:
        file_path = self.output_dir / f"before_after_option_{option_id}.png"
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        file_path.write_bytes(base64.b64decode(image_data))
        return str(file_path)

    async def _generate_single_image(self, prompt: str, option_id: int) -> GeneratedImage:
        self._validate_configuration()
        try:
            response = self._client().images.generate(
                model=self.model,
                prompt=prompt,
                size="1792x1024",
            )
            data = response.data[0]
            if getattr(data, "url", None):
                return GeneratedImage(
                    option_id=option_id, image_url=data.url, prompt_used=prompt, status="success"
                )
            if getattr(data, "b64_json", None):
                path = self._save_base64_image(data.b64_json, option_id)
                return GeneratedImage(
                    option_id=option_id, image_path=path, prompt_used=prompt, status="success"
                )
            return GeneratedImage(
                option_id=option_id,
                prompt_used=prompt,
                status="error",
                error="Image API returned neither URL nor base64 data.",
            )
        except LLMConfigError:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced per-option
            return GeneratedImage(
                option_id=option_id, prompt_used=prompt, status="error", error=str(exc)
            )

    async def generate_images(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        results: list[GeneratedImage] = []
        for option in request.design_options:
            prompt = build_before_after_prompt(
                product_description=request.product_description,
                original_concept=request.original_concept,
                risky_elements=request.risky_elements,
                option=option,
            )
            results.append(await self._generate_single_image(prompt, option.option_id))

        successful = [r for r in results if r.status == "success"]
        failed = [r for r in results if r.status == "error"]
        if successful and not failed:
            status, error = "success", None
        elif successful and failed:
            status = "partial_success"
            error = f"{len(failed)} image(s) failed while {len(successful)} succeeded."
        else:
            status, error = "error", "All image generations failed."

        return ImageGenerationResponse(status=status, images=results, error=error)


__all__ = ["ImageGenerationService"]
