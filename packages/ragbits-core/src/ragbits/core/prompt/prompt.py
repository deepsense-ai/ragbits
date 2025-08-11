import asyncio
import base64
import mimetypes
import textwrap
import warnings
from abc import ABCMeta
from collections.abc import Awaitable, Callable
from typing import Any, Generic, cast, get_args, get_origin, overload

import filetype
from jinja2 import Environment, Template, meta
from pydantic import BaseModel
from typing_extensions import TypeVar, get_original_bases

from ragbits.core.prompt.base import BasePromptWithParser, ChatFormat, PromptOutputT
from ragbits.core.prompt.exceptions import (
    PromptWithAttachmentOfUnknownFormat,
    PromptWithAttachmentOfUnsupportedFormat,
    PromptWithEmptyAttachment,
)
from ragbits.core.prompt.parsers import DEFAULT_PARSERS, build_pydantic_parser

PromptInputT = TypeVar("PromptInputT", bound=BaseModel | None)
FewShotExample = tuple[str | PromptInputT, str | PromptOutputT]


class Attachment(BaseModel):
    """Represents an attachment that can be passed to a LLM."""

    url: str | None = None
    data: bytes | None = None
    mime_type: str | None = None


class Prompt(Generic[PromptInputT, PromptOutputT], BasePromptWithParser[PromptOutputT], metaclass=ABCMeta):
    """
    Generic class for prompts. It contains the system and user prompts, and additional messages.

    To create a new prompt, subclass this class and provide the system and user prompts,
    and optionally the input and output types. The system prompt is optional.
    """

    system_prompt: str | None = None
    user_prompt: str

    # Additional messages to be added to the conversation after the system prompt,
    # pairs of user message and assistant response
    few_shots: list[FewShotExample[PromptInputT, PromptOutputT]] = []

    # function that parses the response from the LLM to specific output type
    # if not provided, the class tries to set it automatically based on the output type
    response_parser: Callable[[str], PromptOutputT | Awaitable[PromptOutputT]]

    # Automatically set in __init_subclass__
    input_type: type[PromptInputT] | None
    output_type: type[PromptOutputT]
    system_prompt_template: Template | None
    user_prompt_template: Template
    image_input_fields: list[str] | None = None

    @classmethod
    def _get_io_types(cls) -> tuple:
        bases = get_original_bases(cls)
        for base in bases:
            if get_origin(base) is Prompt:
                args = get_args(base)
                input_type = args[0] if len(args) > 0 else None
                input_type = None if input_type is type(None) else input_type
                output_type = args[1] if len(args) > 1 else str

                assert input_type is None or issubclass(  # noqa: S101
                    input_type, BaseModel
                ), "Input type must be a subclass of BaseModel"
                return (input_type, output_type)
        return (None, str)

    @classmethod
    def _parse_template(cls, template: str) -> Template:
        env = Environment(autoescape=True)
        ast = env.parse(template)
        template_variables = meta.find_undeclared_variables(ast)
        input_fields = cls.input_type.model_fields.keys() if cls.input_type else set()
        additional_variables = template_variables - input_fields
        if additional_variables:
            raise ValueError(f"Template uses variables that are not present in the input type: {additional_variables}")
        return Template(template)

    @classmethod
    def _render_template(cls, template: Template, input_data: PromptInputT | None) -> str:
        # Workaround for not being able to use `input is not None`
        # because of mypy issue: https://github.com/python/mypy/issues/12622
        context = {}
        if isinstance(input_data, BaseModel):
            context = input_data.model_dump(serialize_as_any=True)
        return template.render(**context)

    @classmethod
    def _get_attachments_from_input_data(cls, input_data: PromptInputT | None | str) -> list[Attachment]:
        attachments: list[Attachment] = []

        if isinstance(input_data, BaseModel):
            # to support backward compatibility with the old image_input_fields:
            image_input_fields = cls.image_input_fields or []
            for field in image_input_fields:
                if image_for_field := getattr(input_data, field):
                    iter_image = [image_for_field] if isinstance(image_for_field, (str | bytes)) else image_for_field
                    attachments.extend(
                        [
                            Attachment(url=image) if isinstance(image, str) else Attachment(data=image)
                            for image in iter_image
                        ]
                    )
            for value in input_data.__dict__.values():
                if isinstance(value, Attachment):
                    attachments.append(value)
                elif isinstance(value, list):
                    attachments.extend([item for item in value if isinstance(item, Attachment)])

        return attachments

    @classmethod
    def _format_message(cls, message: str) -> str:
        return textwrap.dedent(message).strip()

    @classmethod
    def _detect_response_parser(cls) -> Callable[[str], PromptOutputT | Awaitable[PromptOutputT]]:
        if hasattr(cls, "response_parser") and cls.response_parser is not None:
            return cls.response_parser
        if issubclass(cls.output_type, BaseModel):
            return cast(Callable[[str], PromptOutputT], build_pydantic_parser(cls.output_type))
        if cls.output_type in DEFAULT_PARSERS:
            return DEFAULT_PARSERS[cls.output_type]
        raise ValueError(f"Response parser not provided for output type {cls.output_type}")

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        if not hasattr(cls, "user_prompt") or cls.user_prompt is None:
            raise ValueError("User prompt must be provided")

        cls.input_type, cls.output_type = cls._get_io_types()
        cls.system_prompt_template = (
            cls._parse_template(cls._format_message(cls.system_prompt)) if cls.system_prompt else None
        )
        cls.user_prompt_template = cls._parse_template(cls._format_message(cls.user_prompt))
        cls.response_parser = staticmethod(cls._detect_response_parser())

        return super().__init_subclass__(**kwargs)

    @overload
    def __init__(
        self: "Prompt[None, PromptOutputT]", input_data: None = None, history: ChatFormat | None = None
    ) -> None: ...

    @overload
    def __init__(
        self: "Prompt[PromptInputT, PromptOutputT]", input_data: PromptInputT, history: ChatFormat | None = None
    ) -> None: ...

    def __init__(self, input_data: PromptInputT | None = None, history: ChatFormat | None = None) -> None:
        """
        Initialize the Prompt instance.

        Args:
            input_data: The input data to render the prompt templates with. Must be a Pydantic model
                instance if the prompt has an input type defined. If None and input_type is defined,
                a ValueError will be raised.
            history: Optional conversation history to initialize the prompt with. If provided,
                should be in the standard OpenAI chat format.

        Raises:
            ValueError: If input_data is None when input_type is defined, or if input_data
                is a string instead of a Pydantic model.
        """
        if self.input_type and input_data is None:
            raise ValueError("Input data must be provided")

        if isinstance(input_data, str):
            raise ValueError("Input data must be of pydantic model type")

        if self.image_input_fields:
            warnings.warn(
                message="The 'image_input_fields' attribute is deprecated. "
                "Use 'Attachment' objects in the prompt input instead.",
                category=UserWarning,
                stacklevel=2,
            )

        self.rendered_system_prompt = (
            self._render_template(self.system_prompt_template, input_data) if self.system_prompt_template else None
        )
        self.attachments = self._get_attachments_from_input_data(input_data)

        # Additional few shot examples that can be added dynamically using methods
        # (in opposite to the static `few_shots` attribute which is defined in the class)
        self._instance_few_shots: list[FewShotExample[PromptInputT, PromptOutputT]] = []

        # Additional conversation history that can be added dynamically using methods
        self._conversation_history: list[dict[str, Any]] = history or []

        self.add_user_message(input_data or self._render_template(self.user_prompt_template, input_data))
        self.rendered_user_prompt = self.chat[-1]["content"]
        super().__init__()

    @property
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        chat = [
            *(
                [{"role": "system", "content": self.rendered_system_prompt}]
                if self.rendered_system_prompt is not None
                else []
            ),
            *self.list_few_shots(),
            *self._conversation_history,
        ]
        return chat

    def add_few_shot(
        self, user_message: str | PromptInputT, assistant_message: str | PromptOutputT
    ) -> "Prompt[PromptInputT, PromptOutputT]":
        """
        Add a few-shot example to the conversation.

        Args:
            user_message (str | PromptInputT): The raw user message or input data that will be rendered using the
                user prompt template.
            assistant_message (str | PromptOutputT): The raw assistant response or output data that will be cast to a
                string or in case of a Pydantic model, to JSON.

        Returns:
            Prompt[PromptInputT, PromptOutputT]: The current prompt instance in order to allow chaining.
        """
        self._instance_few_shots.append((user_message, assistant_message))
        return self

    def list_few_shots(self) -> ChatFormat:
        """
        Returns the few shot examples in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        result: ChatFormat = []
        user_content: str | list[dict[str, Any]]
        for user_message, assistant_message in self.few_shots + self._instance_few_shots:
            if not isinstance(user_message, str):
                rendered_text_message = self._render_template(self.user_prompt_template, user_message)
                input_attachments = self._get_attachments_from_input_data(user_message)

                user_parts: list[dict[str, Any]] = [{"type": "text", "text": rendered_text_message}]
                for attachment in input_attachments:
                    user_parts.append(self.create_message_with_attachment(attachment))

                user_content = user_parts if len(user_parts) > 1 else rendered_text_message

            else:
                user_content = user_message

            if isinstance(assistant_message, BaseModel):
                assistant_content = assistant_message.model_dump_json()
            else:
                assistant_content = str(assistant_message)

            result.append({"role": "user", "content": user_content})
            result.append({"role": "assistant", "content": assistant_content})
        return result

    def add_user_message(self, message: str | dict[str, Any] | PromptInputT) -> "Prompt[PromptInputT, PromptOutputT]":  # type: ignore
        """
        Add a user message to the conversation history.

        Args:
            message (str | dict[str, Any] | PromptInputT): The user message content. Can be:
                - A string: Used directly as content
                - A dictionary: With format {"type": "text", "text": "message"} or image content
                - An PromptInputT model: Will be rendered using the user prompt template

        Returns:
            Prompt[PromptInputT, PromptOutputT]: The current prompt instance to allow chaining.
        """
        content: str | list[dict[str, Any]] | dict[str, Any]

        if isinstance(message, BaseModel):
            # Type checking to ensure we're passing PromptInputT to the methods
            input_model: PromptInputT = cast(PromptInputT, message)

            # Render the message using the template if it's an input model
            rendered_text = self._render_template(self.user_prompt_template, input_model)
            input_attachments = self._get_attachments_from_input_data(input_model)

            content_list: list[dict[str, Any]] = [{"type": "text", "text": rendered_text}]
            for attachment in input_attachments:
                content_list.append(self.create_message_with_attachment(attachment))

            content = content_list if len(content_list) > 1 else rendered_text
        else:
            content = cast(str | dict[str, Any], message)

        return super().add_user_message(content)

    def list_images(self) -> list[str]:
        """
        Returns the images in form of URLs or base64 encoded strings.

        Returns:
            list of images
        """
        return [
            content["image_url"]["url"]
            for message in self.chat
            if message["content"]
            for content in message["content"]
            if isinstance(message["content"], list) and content["type"] == "image_url"
        ]

    def list_pdfs(self) -> list[str]:  # noqa: PLR6301
        """
        Returns the PDFs in form of URLs or base64 encoded strings.

        Returns:
            list of PDFs
        """
        return [
            content["file"].get("file_id") or content["file"]["file_data"]
            for message in self.chat
            if message["content"]
            for content in message["content"]
            if isinstance(message["content"], list) and content["type"] == "file"
        ]

    @staticmethod
    def create_message_with_attachment(attachment: Attachment) -> dict[str, Any]:
        """
        Create a message with an attachment in the OpenAI chat format.

        Args:
            attachment (Attachment): The attachment to include in the message.

        Returns:
            dict[str, Any]: A dictionary representing the message with the attachment.
        """
        if not (attachment.data or attachment.url):
            raise PromptWithEmptyAttachment()

        def get_mime_type() -> str:
            if attachment.mime_type:
                return attachment.mime_type
            if attachment.data:
                detected = filetype.guess(attachment.data)
                if detected:
                    return detected.mime
            if attachment.url:
                guessed_type, _ = mimetypes.guess_type(attachment.url)
                if guessed_type:
                    return guessed_type
            raise PromptWithAttachmentOfUnknownFormat()

        def encode_data_url(data: bytes, mime: str) -> str:
            return f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"

        mime_type = get_mime_type()

        if mime_type.startswith("image/"):
            return {
                "type": "image_url",
                "image_url": {
                    "url": attachment.url or encode_data_url(attachment.data, mime_type)  # type: ignore[arg-type]
                },
            }

        if mime_type == "application/pdf":
            return {
                "type": "file",
                "file": {"file_id": attachment.url}
                if attachment.url
                else {"file_data": encode_data_url(attachment.data, mime_type)},  # type: ignore[arg-type]
            }

        raise PromptWithAttachmentOfUnsupportedFormat(mime_type)

    def output_schema(self) -> dict | type[BaseModel] | None:
        """
        Returns the schema of the desired output. Can be used to request structured output from the LLM API
        or to validate the output. Can return either a Pydantic model or a JSON schema.

        Returns:
            Optional[Dict | Type[BaseModel]]: The schema of the desired output or the model describing it.
        """
        return self.output_type if issubclass(self.output_type, BaseModel) else None

    @property
    def json_mode(self) -> bool:
        """
        Returns whether the prompt should be sent in JSON mode.

        Returns:
            bool: Whether the prompt should be sent in JSON mode.
        """
        return issubclass(self.output_type, BaseModel)

    async def parse_response(self, response: str) -> PromptOutputT:
        """
        Parse the response from the LLM to the desired output type.

        Args:
            response (str): The response from the LLM.

        Returns:
            PromptOutputT: The parsed response.

        Raises:
            ResponseParsingError: If the response cannot be parsed.
        """
        if asyncio.iscoroutinefunction(self.response_parser):
            result = await self.response_parser(response)
        else:
            result = self.response_parser(response)
        return result

    @classmethod
    def to_promptfoo(cls, config: dict[str, Any]) -> ChatFormat:
        """
        Generate a prompt in the promptfoo format from a promptfoo test configuration.

        Args:
            config: The promptfoo test configuration.

        Returns:
            ChatFormat: The prompt in the format used by promptfoo.
        """
        return cls(cls.input_type.model_validate(config["vars"])).chat  # type: ignore
