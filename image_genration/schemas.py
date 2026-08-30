from typing import List, Optional
from pydantic import BaseModel, Field


class DesignOption(BaseModel):
    """
    One redesign option produced by Agent 4.
    """

    option_id: int = Field(..., description="Unique option identifier")

    title: str = Field(
        ...,
        description="Short title for the redesign option"
    )

    description: str = Field(
        ...,
        description="Description of the redesigned engineering concept"
    )

    key_changes: List[str] = Field(
        default_factory=list,
        description="Important engineering changes introduced by this option"
    )


class ImageGenerationRequest(BaseModel):
    """
    Input to the image-generation layer.
    """

    product_description: str = Field(
        ...,
        min_length=1,
        description="Original product description"
    )

    original_concept: Optional[str] = Field(
        default=None,
        description="Description of the original product/system concept"
    )

    risky_elements: List[str] = Field(
        default_factory=list,
        description="Potentially risky claim elements identified by Agent 2/3"
    )

    design_options: List[DesignOption] = Field(
        ...,
        min_length=1,
        description="Redesign options produced by Agent 4"
    )


class GeneratedImage(BaseModel):
    """
    Result for one generated image.
    """

    option_id: int

    image_url: Optional[str] = None

    image_path: Optional[str] = None

    prompt_used: str

    status: str = "success"

    error: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """
    Complete image-generation response.
    """

    status: str

    images: List[GeneratedImage]

    error: Optional[str] = None