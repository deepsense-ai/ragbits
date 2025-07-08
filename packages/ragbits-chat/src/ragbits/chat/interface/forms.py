from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import deprecated


@deprecated("FeedbackForm is deprecated. You can use standard pydantic models instead as like_form and dislike_form.")
class FormField(BaseModel):
    """Field in a feedback form."""

    name: str = Field(description="Name of the field")
    type: str = Field(description="Type of the field (text, select, etc.)")
    required: bool = Field(description="Whether the field is required")
    label: str = Field(description="Display label for the field")
    options: list[str] | None = Field(None, description="Options for select fields")


@deprecated("FeedbackForm is deprecated. You can use standard pydantic models instead as like_form and dislike_form.")
class FeedbackForm(BaseModel):
    """Model for feedback form structure."""

    title: str = Field(description="Title of the form")
    fields: list[FormField] = Field(description="Fields in the form")


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

    def __init__(
        self,
        like_enabled: bool = False,
        like_form: type[BaseModel] | FeedbackForm | None = None,
        dislike_enabled: bool = False,
        dislike_form: type[BaseModel] | FeedbackForm | None = None,
    ) -> None:
        like_form_json_schema = None
        dislike_form_json_schema = None

        if like_form:
            if isinstance(like_form, FeedbackForm):
                like_form_json_schema = self._map_to_json_schema(like_form)
            else:
                like_form_json_schema = like_form.model_json_schema()
        if dislike_form:
            if isinstance(dislike_form, FeedbackForm):
                dislike_form_json_schema = self._map_to_json_schema(dislike_form)
            else:
                dislike_form_json_schema = dislike_form.model_json_schema()

        super().__init__(
            like_enabled=like_enabled,
            like_form=like_form_json_schema,
            dislike_enabled=dislike_enabled,
            dislike_form=dislike_form_json_schema,
        )

    @staticmethod
    def _map_to_json_schema(feedback_config: FeedbackForm) -> dict[str, Any]:
        """Maps deprecated FeedbackFrom to valid JSONSchema format."""

        def map_field(field: FormField) -> dict[str, Any]:
            """Maps given field to JSONSchema representation"""
            properties: dict[str, Any] = {
                "title": " ".join(field.name.split("_")).title(),
                "description": field.label,
                "type": "string",
            }

            if field.required and field.type == "text":
                properties["minLength"] = 1

            if field.options:
                properties["enum"] = field.options

            return properties

        required_fields = [field.name for field in feedback_config.fields if field.required]
        properties = {field.name: map_field(field) for field in feedback_config.fields}

        return {"title": feedback_config.title, "type": "object", "required": required_fields, "properties": properties}


class UserSettings(BaseModel):
    """Configuration for chat options."""

    form: dict[str, Any] | None = Field(
        default=None,
        description="The form to use for chat options. Use Pydantic models to define form objects, "
        "that would get converted to JSONSchema and rendered in the UI.",
    )

    def __init__(
        self,
        form: type[BaseModel] | None = None,
    ) -> None:
        form_json_schema = None

        if form:
            form_json_schema = form.model_json_schema()

        super().__init__(form=form_json_schema)
