from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import deprecated


@deprecated("Use JSONSchemaFeedbackConfig instead")
class FormField(BaseModel):
    """Field in a feedback form."""

    name: str = Field(description="Name of the field")
    type: str = Field(description="Type of the field (text, select, etc.)")
    required: bool = Field(description="Whether the field is required")
    label: str = Field(description="Display label for the field")
    options: list[str] | None = Field(None, description="Options for select fields")


@deprecated("Use JSONSchemaFeedbackConfig instead")
class FeedbackForm(BaseModel):
    """Model for feedback form structure."""

    title: str = Field(description="Title of the form")
    fields: list[FormField] = Field(description="Fields in the form")


@deprecated("Use JSONSchemaFeedbackConfig instead")
class FeedbackConfig(BaseModel):
    """Configuration for feedback collection."""

    like_enabled: bool = Field(default=False, description="Whether like feedback is enabled")
    like_form: FeedbackForm | None = Field(default=None, description="The form to use for like feedback")

    dislike_enabled: bool = Field(default=False, description="Whether dislike feedback is enabled")
    dislike_form: FeedbackForm | None = Field(default=None, description="The form to use for dislike feedback")


class JSONSchemaFeedbackConfig(BaseModel):
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
    ) -> "JSONSchemaFeedbackConfig":
        """Create FeedbackConfig from form models"""
        return cls(
            like_enabled=like_enabled,
            like_form=like_form.model_json_schema() if like_form else None,
            dislike_enabled=dislike_enabled,
            dislike_form=dislike_form.model_json_schema() if dislike_form else None,
        )
