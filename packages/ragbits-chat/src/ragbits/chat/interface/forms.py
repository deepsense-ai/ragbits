from pydantic import BaseModel, Field


class FeedbackConfig(BaseModel):
    """Configuration for feedback collection."""

    like_enabled: bool = Field(default=False, description="Whether like feedback is enabled")
    like_form: BaseModel | None = Field(
        default=None,
        description=(
            "The form to use for like feedback. Use Pydantic models to define form objects, "
            "that would get converted to JSONSchema and rendered in the UI."
        ),
    )

    dislike_enabled: bool = Field(default=False, description="Whether dislike feedback is enabled")
    dislike_form: BaseModel | None = Field(
        default=None,
        description=(
            "The form to use for dislike feedback. Use Pydantic models to define form objects, "
            "that would get converted to JSONSchema and rendered in the UI."
        ),
    )
