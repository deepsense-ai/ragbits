from collections.abc import Awaitable, Callable
from inspect import iscoroutinefunction
from typing import Any

from pydantic import BaseModel


class _UnboundedToolDefinition(BaseModel):
    """
    Definition of a tool.
    """

    name: str
    description: str

    def bind(self, method: Callable) -> "ToolDefinition":
        """
        Bind the tool definition to a method.

        Args:
            method: The method to bind the tool definition to.

        Returns:
            Tool definition with the method bound.
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            func=method,
        )


class ToolDefinition:
    """
    Definition of a tool.
    """

    name: str
    description: str
    func: Callable[..., Awaitable[Any]]

    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func


class Tool:
    """
    Indicates that a class can be used as a tool. One class can expose multiple methods as tools.
    To mark a method as a tool, use the `@Tool.define` decorator.
    """

    @staticmethod
    def define(name: str | None = None, description: str | None = None) -> Callable:
        """
        Decorator for marking a method as a tool definition.

        Args:
            name: The name of the tool.
            description: The description of the tool.

        Returns:
            Function that returns the decorated method
        """

        def wrapped(func: Callable) -> Callable:  # pylint: disable=missing-return-doc
            if not iscoroutinefunction(func):
                raise ValueError("Tool methods must be async")

            func._toolDefinition = _UnboundedToolDefinition(  # type:ignore # pylint: disable=protected-access
                name=name or func.__name__,
                description=description or func.__doc__ or "",
            )
            return func

        return wrapped

    def get_available_tools(self) -> dict[str, ToolDefinition]:
        """
        Get all available tools.

        Returns:
            Dict with all available tools.
        """
        return {
            tool.name: tool
            for tool in (
                member._toolDefinition.bind(member)  # type:ignore # pylint: disable=protected-access
                for member in (getattr(self, name) for name in dir(self))
                if hasattr(member, "_toolDefinition")
            )
        }
