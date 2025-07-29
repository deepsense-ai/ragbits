from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from typing_extensions import Self

from ragbits.core.utils.function_schema import convert_function_to_function_schema, get_context_variable_name
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from pydantic_ai import Tool as PydanticAITool

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
    """The output from the tool call."""


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
