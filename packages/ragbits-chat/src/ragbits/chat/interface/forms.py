from typing import Any

from pydantic import BaseModel, Field, field_validator


class FeedbackConfig(BaseModel):
    """Configuration for feedback collection."""

    like_enabled: bool = Field(default=False, description="Whether like feedback is enabled")
    like_form: dict[str, Any] | None = Field(
        default=None,
        description=(
            "The form to use for like feedback. Use Pydantic models to define form objects, "
            "that would get converted to JSONSchema and rendered in the UI."
        ),
    )

    dislike_enabled: bool = Field(default=False, description="Whether dislike feedback is enabled")
    dislike_form: dict[str, Any] | None = Field(
        default=None,
        description=(
            "The form to use for dislike feedback. Use Pydantic models to define form objects, "
            "that would get converted to JSONSchema and rendered in the UI."
        ),
    )

    @field_validator("like_form", "dislike_form", mode="before")
    @classmethod
    def transform(cls, raw: BaseModel | None) -> dict[str, Any] | None:
        """Transform the passed Pydantic model to JSONSchema"""
        if not raw:
            return None

        return raw.model_json_schema()
