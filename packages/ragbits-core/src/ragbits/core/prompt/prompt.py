import textwrap
from abc import ABCMeta
from typing import Any, Callable, Dict, Generic, Optional, Tuple, Type, cast, get_args, get_origin, overload

from jinja2 import Environment, Template, meta
from pydantic import BaseModel
from typing_extensions import TypeVar, get_original_bases

from .base import BasePromptWithParser, ChatFormat, OutputT
from .parsers import DEFAULT_PARSERS, build_pydantic_parser

InputT = TypeVar("InputT", bound=Optional[BaseModel])
FewShotExample = Tuple[str | InputT, str | OutputT]


class Prompt(Generic[InputT, OutputT], BasePromptWithParser[OutputT], metaclass=ABCMeta):
    """
    Generic class for prompts. It contains the system and user prompts, and additional messages.

    To create a new prompt, subclass this class and provide the system and user prompts,
    and optionally the input and output types. The system prompt is optional.
    """

    system_prompt: Optional[str] = None
    user_prompt: str

    # Additional messages to be added to the conversation after the system prompt,
    # pairs of user message and assistant response
    few_shots: list[FewShotExample[InputT, OutputT]] = []

    # function that parses the response from the LLM to specific output type
    # if not provided, the class tries to set it automatically based on the output type
    response_parser: Callable[[str], OutputT]

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
                input_type = None if input_type is type(None) else input_type
                output_type = args[1] if len(args) > 1 else str

                assert input_type is None or issubclass(
                    input_type, BaseModel
                ), "Input type must be a subclass of BaseModel"
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
    def _detect_response_parser(cls) -> Callable[[str], OutputT]:
        if hasattr(cls, "response_parser") and cls.response_parser is not None:
            return cls.response_parser
        if issubclass(cls.output_type, BaseModel):
            return cast(Callable[[str], OutputT], build_pydantic_parser(cls.output_type))
        if cls.output_type in DEFAULT_PARSERS:
            return DEFAULT_PARSERS[cls.output_type]
        raise ValueError(f"Response parser not provided for output type {cls.output_type}")

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
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
    def __init__(self: "Prompt[None, OutputT]") -> None:
        ...

    @overload
    def __init__(self: "Prompt[InputT, OutputT]", input_data: InputT) -> None:
        ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        input_data = args[0] if args else kwargs.get("input_data")
        if self.input_type and input_data is None:
            raise ValueError("Input data must be provided")

        self.rendered_system_prompt = (
            self._render_template(self.system_prompt_template, input_data) if self.system_prompt_template else None
        )
        self.rendered_user_prompt = self._render_template(self.user_prompt_template, input_data)

        # Additional few shot examples that can be added dynamically using methods
        # (in opposite to the static `few_shots` attribute which is defined in the class)
        self._instace_few_shots: list[FewShotExample[InputT, OutputT]] = []
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
            {"role": "user", "content": self.rendered_user_prompt},
        ]
        return chat

    def add_few_shot(self, user_message: str | InputT, assistant_message: str | OutputT) -> "Prompt[InputT, OutputT]":
        """
        Add a few-shot example to the conversation.

        Args:
            user_message (str | InputT): The raw user message or input data that will be rendered using the
                user prompt template.
            assistant_message (str | OutputT): The raw assistant response or output data that will be cast to a string
                or in case of a Pydantic model, to JSON.

        Returns:
            Prompt[InputT, OutputT]: The current prompt instance in order to allow chaining.
        """
        self._instace_few_shots.append((user_message, assistant_message))
        return self

    def list_few_shots(self) -> ChatFormat:
        """
        Returns the few shot examples in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        result: ChatFormat = []
        for user_message, assistant_message in self.few_shots + self._instace_few_shots:
            if not isinstance(user_message, str):
                user_message = self._render_template(self.user_prompt_template, user_message)

            if isinstance(assistant_message, BaseModel):
                assistant_message = assistant_message.model_dump_json()
            else:
                assistant_message = str(assistant_message)

            result.append({"role": "user", "content": user_message})
            result.append({"role": "assistant", "content": assistant_message})
        return result

    def output_schema(self) -> Optional[Dict | Type[BaseModel]]:
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

    def parse_response(self, response: str) -> OutputT:
        """
        Parse the response from the LLM to the desired output type.

        Args:
            response (str): The response from the LLM.

        Returns:
            OutputT: The parsed response.

        Raises:
            ResponseParsingError: If the response cannot be parsed.
        """
        return self.response_parser(response)

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
