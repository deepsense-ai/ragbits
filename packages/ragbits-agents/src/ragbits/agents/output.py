from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from typing_extensions import Self

from ragbits.core.utils.function_schema import convert_function_to_function_schema, get_context_variable_name


@dataclass
class OutputCallResult:
    """
    Filtered results
    """

    id: str
    """Unique identifier of the given output"""
    output_type: str
    """Type of the given output"""
    result: Any
    """Filtered result"""


@dataclass
class OutputFunction:
    """
    Output function that can be handled by agent
    """

    name: str
    """The name of the output function."""
    description: str | None
    """Optional description of what the output function does."""
    parameters: dict[str, Any]
    """Dictionary containing the parameters JSON schema."""
    on_tool_call: Callable
    """The actual callable function to execute when the tool is called."""
    context_var_name: str | None = None
    """The name of the context variable that this tool accepts."""

    @classmethod
    def from_callable(cls, callable: Callable) -> Self:
        """
        Create a OutputFunction instance from a callable function.

        Args:
            callable: The function to convert into a OutputFunction

        Returns:
            A new OutputFunction instance representing the callable function.
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
