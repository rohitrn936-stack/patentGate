import base64
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .prompts import build_before_after_prompt
from .schemas import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageGenerationResponse,
)

load_dotenv()


class ImageGenerationService:
    """
    Service responsible for generating Before/After engineering
    concept images from Agent 4 redesign options.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("IMAGE_API_KEY")
        self.model = model or os.getenv("IMAGE_MODEL")

        self.output_dir = Path(
            output_dir
            or os.getenv(
                "IMAGE_OUTPUT_DIR",
                "generated_images"
            )
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def _validate_configuration(self):
        """
        Validate API configuration before making a request.
        """

        if not self.api_key:
            raise RuntimeError(
                "IMAGE_API_KEY is empty or missing."
            )

        if not self.model:
            raise RuntimeError(
                "IMAGE_MODEL is empty or missing."
            )

    def _save_base64_image(
        self,
        image_data: str,
        option_id: int,
    ) -> str:
        """
        Save base64 image data locally.
        """

        file_path = (
            self.output_dir
            / f"before_after_option_{option_id}.png"
        )

        # Handle data URLs such as:
        # data:image/png;base64,....

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        with open(file_path, "wb") as file:
            file.write(image_bytes)

        return str(file_path)

    async def _generate_single_image(
        self,
        prompt: str,
        option_id: int,
    ) -> GeneratedImage:
        """
        Generate one image.

        Provider-specific implementation lives here.
        """

        self._validate_configuration()

        try:
            # Import here so the rest of the project can still load
            # even when the image provider SDK is not installed.
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key
            )

            response = client.images.generate(
                model=self.model,
                prompt=prompt,
                size="1792x1024",
            )

            image_data = response.data[0]

            # Some image APIs return a URL.
            image_url = getattr(
                image_data,
                "url",
                None
            )

            if image_url:
                return GeneratedImage(
                    option_id=option_id,
                    image_url=image_url,
                    prompt_used=prompt,
                    status="success",
                )

            # Some APIs return base64 image data.
            b64_json = getattr(
                image_data,
                "b64_json",
                None
            )

            if b64_json:
                image_path = self._save_base64_image(
                    b64_json,
                    option_id,
                )

                return GeneratedImage(
                    option_id=option_id,
                    image_path=image_path,
                    prompt_used=prompt,
                    status="success",
                )

            return GeneratedImage(
                option_id=option_id,
                prompt_used=prompt,
                status="error",
                error="Image API returned neither URL nor base64 image data.",
            )

        except Exception as exc:
            return GeneratedImage(
                option_id=option_id,
                prompt_used=prompt,
                status="error",
                error=str(exc),
            )

    async def generate_images(
        self,
        request: ImageGenerationRequest,
    ) -> ImageGenerationResponse:
        """
        Generate one image for every Agent 4 redesign option.
        """

        results: list[GeneratedImage] = []

        for option in request.design_options:

            prompt = build_before_after_prompt(
                product_description=request.product_description,
                original_concept=request.original_concept,
                risky_elements=request.risky_elements,
                option=option,
            )

            result = await self._generate_single_image(
                prompt=prompt,
                option_id=option.option_id,
            )

            results.append(result)

        successful = [
            result
            for result in results
            if result.status == "success"
        ]

        failed = [
            result
            for result in results
            if result.status == "error"
        ]

        if successful and not failed:
            status = "success"
            error = None

        elif successful and failed:
            status = "partial_success"
            error = (
                f"{len(failed)} image(s) failed "
                f"while {len(successful)} succeeded."
            )

        else:
            status = "error"
            error = "All image generations failed."

        return ImageGenerationResponse(
            status=status,
            images=results,
            error=error,
        )