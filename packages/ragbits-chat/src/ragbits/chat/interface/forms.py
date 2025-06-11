from typing import Any

from pydantic import BaseModel, Field


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

    @classmethod
    def from_models(
        cls,
        like_enabled: bool,
        like_form: type[BaseModel] | None,
        dislike_enabled: bool,
        dislike_form: type[BaseModel] | None,
    ) -> "FeedbackConfig":
        """Create FeedbackConfig from form models"""
        return cls(
            like_enabled=like_enabled,
            like_form=like_form.model_json_schema() if like_form else None,
            dislike_enabled=dislike_enabled,
            dislike_form=dislike_form.model_json_schema() if dislike_form else None,
        )
