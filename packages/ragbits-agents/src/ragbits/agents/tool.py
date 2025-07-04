from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from typing_extensions import Self

from ragbits.core.utils.function_schema import convert_function_to_function_schema


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
