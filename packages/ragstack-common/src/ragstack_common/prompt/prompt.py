import textwrap
from abc import ABCMeta
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, Union, get_args, get_origin, overload

from jinja2 import Environment, Template, meta
from pydantic import BaseModel
from typing_extensions import TypeVar, get_original_bases

InputT = TypeVar("InputT", bound=Optional[BaseModel])
OutputT = TypeVar("OutputT", bound=Union[str, BaseModel])

ChatFormat = List[Dict[str, str]]


class Prompt(Generic[InputT, OutputT], metaclass=ABCMeta):
    """
    Generic class for prompts. It contains the system and user prompts, and additional messages.
    """

    system_prompt: Optional[str] = None
    user_prompt: str
    additional_messages: ChatFormat = []

    # Automatically set in __init_subclass__
    input_type: Optional[Type[InputT]]
    output_type: Type[OutputT]
    system_prompt_template: Optional[Template]
    user_prompt_template: Template

    @classmethod
    def _get_io_types(cls) -> Tuple:
        bases = get_original_bases(cls)
        for base in bases:
            if get_origin(base) is Prompt:
                args = get_args(base)
                input_type = args[0] if len(args) > 0 else None
                output_type = args[1] if len(args) > 1 else str
                assert input_type is None or issubclass(
                    input_type, BaseModel
                ), "Input type must be a subclass of BaseModel"
                assert output_type is str or issubclass(
                    output_type, BaseModel
                ), "Output type must be a subclass of BaseModel or str"
                return (input_type, output_type)
        return (None, str)

    @classmethod
    def _parse_template(cls, template: str) -> Template:
        env = Environment()  # nosec B701 - HTML autoescaping not needed for plain text
        ast = env.parse(template)
        template_variables = meta.find_undeclared_variables(ast)
        input_fields = cls.input_type.model_fields.keys() if cls.input_type else set()
        additional_variables = template_variables - input_fields
        if additional_variables:
            raise ValueError(f"Template uses variables that are not present in the input type: {additional_variables}")
        return Template(template)

    @classmethod
    def _render_template(cls, template: Template, input_data: Optional[InputT]) -> str:
        # Workaround for not being able to use `input is not None`
        # because of mypy issue: https://github.com/python/mypy/issues/12622
        context = {}
        if isinstance(input_data, BaseModel):
            context = input_data.model_dump()
        return template.render(**context)

    @classmethod
    def _format_message(cls, message: str) -> str:
        return textwrap.dedent(message).strip()

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        if not hasattr(cls, "user_prompt") or cls.user_prompt is None:
            raise ValueError("User prompt must be provided")

        cls.input_type, cls.output_type = cls._get_io_types()
        cls.system_prompt_template = (
            cls._parse_template(cls._format_message(cls.system_prompt)) if cls.system_prompt else None
        )
        cls.user_prompt_template = cls._parse_template(cls._format_message(cls.user_prompt))

        return super().__init_subclass__(**kwargs)

    @overload
    def __init__(self: "Prompt[None, OutputT]") -> None:
        ...

    @overload
    def __init__(self: "Prompt[InputT, OutputT]", input_data: InputT) -> None:
        ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        input_data = args[0] if args else kwargs.get("input_data")
        if self.input_type and input_data is None:
            raise ValueError("Input data must be provided")

        self.system_message = (
            self._render_template(self.system_prompt_template, input_data) if self.system_prompt_template else None
        )
        self.user_message = self._render_template(self.user_prompt_template, input_data)
        super().__init__()

    @property
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        return [
            *([{"role": "system", "content": self.system_message}] if self.system_message is not None else []),
            {"role": "user", "content": self.user_message},
        ] + self.additional_messages

    def add_user_message(self, message: str) -> "Prompt[InputT, OutputT]":
        """
        Add a message from the user to the conversation.

        Args:
            message (str): The message to add.

        Returns:
            Prompt[InputT, OutputT]: The current prompt instance in order to allow chaining.
        """
        self.additional_messages.append({"role": "user", "content": message})
        return self

    def add_assistant_message(self, message: str) -> "Prompt[InputT, OutputT]":
        """
        Add a message from the assistant to the conversation.

        Args:
            message (str): The message to add.

        Returns:
            Prompt[InputT, OutputT]: The current prompt instance in order to allow chaining.
        """
        self.additional_messages.append({"role": "assistant", "content": message})
        return self

    @classmethod
    def output_schema(cls) -> Optional[Dict]:
        """
        Returns the JSON schema of the desired output. Can be used to request structured output from the LLM API
        or to validate the output.

        Returns:
            Optional[Dict]: The JSON schema of the output (None if no Pydantic model was given).
        """
        if issubclass(cls.output_type, BaseModel):
            return cls.output_type.model_json_schema()
        return None

    @property
    def json_mode(self) -> bool:
        """
        Returns whether the prompt should be sent in JSON mode.

        Returns:
            bool: Whether the prompt should be sent in JSON mode.
        """
        return issubclass(self.output_type, BaseModel)
