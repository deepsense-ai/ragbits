from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT
from ragbits.core.utils.decorators import requires_dependencies
from ragbits.core.utils.function_schema import convert_function_to_function_schema, get_context_variable_name

if TYPE_CHECKING:
    from ragbits.agents import Agent, AgentResultStreaming, AgentRunContext

with suppress(ImportError):
    from pydantic_ai import Tool as PydanticAITool


@dataclass
class ToolReturn:
    """
    Represents an object returned from the tool. If a tool wants to return a value with some content hidden
    from LLM, it needs to return an object of this class directly.
    """

    value: Any
    "Value passed directly to LLM as a result of the tool"
    metadata: Any = None
    "Metadata not passed to the LLM, but which can be used in the application later on"


@dataclass
class ToolCallResult:
    """
    Result of the tool call.
    """

    id: str
    """Unique identifier for the specific tool call instance."""
    name: str
    """Name of the tool that was called."""
    arguments: dict[str, Any]
    """Dictionary containing the arguments passed to the tool"""
    result: Any
    """The output from the tool call passed to the LLM"""
    metadata: Any = None
    """Metadata returned from a tool that is not meant to be seen by the LLM"""


@dataclass
class Tool:
    """
    Function tool that can be called by the agent.
    """

    name: str
    """The name of the tool/function."""
    description: str | None
    """Optional description of what the tool does."""
    parameters: dict[str, Any]
    """Dictionary containing the parameters JSON schema."""
    on_tool_call: Callable
    """The actual callable function to execute when the tool is called."""
    context_var_name: str | None = None
    """The name of the context variable that this tool accepts."""
    id: str | None = None

    @classmethod
    def from_callable(cls, callable: Callable) -> Self:
        """
        Create a Tool instance from a callable function.

        Args:
            callable: The function to convert into a Tool

        Returns:
            A new Tool instance representing the callable function.
        """
        schema = convert_function_to_function_schema(callable)

        return cls(
            name=schema["function"]["name"],
            description=schema["function"]["description"],
            parameters=schema["function"]["parameters"],
            on_tool_call=callable,
            context_var_name=get_context_variable_name(callable),
        )

    def to_function_schema(self) -> dict[str, Any]:
        """
        Convert the Tool to a standardized function schema format.

        Returns:
            Function schema dictionary with 'type' and 'function' keys.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @requires_dependencies("pydantic_ai")
    def to_pydantic_ai(self) -> "PydanticAITool":
        """
        Convert ragbits tool to a Pydantic AI Tool.

        Returns:
            A `pydantic_ai.tools.Tool` object.
        """
        return PydanticAITool(
            function=self.on_tool_call,
            name=self.name,
            description=self.description,
        )

    @classmethod
    def from_agent(
        cls,
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        name: str | None = None,
        description: str | None = None,
    ) -> "Tool":
        """
        Wraps a downstream agent as a single tool. The tool parameters are inferred from
        the downstream agent's prompt input.

        Args:
            agent: The downstream agent to wrap as a tool.
            name: Optional override for the tool name.
            description: Optional override for the tool description.

        Returns:
            Tool instance representing the agent.
        """
        display_name = name or agent.name or "agent"
        variable_name = display_name.replace(" ", "_").lower()
        description = description or agent.description

        input_model_cls = getattr(agent.prompt, "input_type", None)
        if input_model_cls and issubclass(input_model_cls, BaseModel):
            fields = input_model_cls.model_fields
            properties = {}
            required = list(fields.keys())

            for field_name in fields:
                param_desc = None
                for t in getattr(agent, "tools", []):
                    t_params = getattr(t, "parameters", {}).get("properties", {})
                    if field_name in t_params:
                        param_desc = t_params[field_name].get("description")
                        break

                properties[field_name] = {
                    "type": "string",
                    "title": field_name.capitalize(),
                    "description": param_desc,
                }
        else:
            properties = {"input": {"type": "string", "description": "Input for the downstream agent"}}
            required = ["input"]

        parameters = {"type": "object", "properties": properties, "required": required}

        context_var_name = get_context_variable_name(agent.run)

        def _on_tool_call(**kwargs: dict) -> "AgentResultStreaming":
            if context_var_name:
                context = cast("AgentRunContext[Any] | None", kwargs.get(context_var_name))
                if context is not None:
                    context.register_agent(cast("Agent[Any, Any, str]", agent))

            if input_model_cls and issubclass(input_model_cls, BaseModel):
                model_input = input_model_cls(**kwargs)
            else:
                model_input = kwargs.get("input")

            return agent.run_streaming(model_input, context=context)

        return cls(
            name=variable_name,
            id=agent.id,
            description=description,
            parameters=parameters,
            on_tool_call=_on_tool_call,
            context_var_name=context_var_name,
        )


ToolChoice = Literal["auto", "none", "required"] | Callable
