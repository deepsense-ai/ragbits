from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ImageGenerationResponse(BaseModel):
    """Result from image generation tool."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields

    image_path: Path | str | None = Field(description="Path to the generated image file, None if generation failed")
    output_text: str = Field(description="Text output from the image generation process")
