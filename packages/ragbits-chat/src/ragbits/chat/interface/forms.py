from pydantic import BaseModel, Field


class FormField(BaseModel):
    """Field in a feedback form."""

    name: str = Field(description="Name of the field")
    type: str = Field(description="Type of the field (text, select, etc.)")
    required: bool = Field(description="Whether the field is required")
    label: str = Field(description="Display label for the field")
    options: list[str] | None = Field(None, description="Options for select fields")


class FeedbackForm(BaseModel):
    """Model for feedback form structure."""

    title: str = Field(description="Title of the form")
    fields: list[FormField] = Field(description="Fields in the form")


class FeedbackConfig(BaseModel):
    """Configuration for feedback collection."""

    like_enabled: bool = Field(default=False, description="Whether like feedback is enabled")
    like_form: FeedbackForm | None = Field(default=None, description="The form to use for like feedback")

    dislike_enabled: bool = Field(default=False, description="Whether dislike feedback is enabled")
    dislike_form: FeedbackForm | None = Field(default=None, description="The form to use for dislike feedback")
