"""
Hook manager for organizing and executing hooks.

This module provides the HookManager class which handles registration,
organization, and execution of hooks during lifecycle events.
"""

from __future__ import annotations

from collections import defaultdict

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, HookInput, HookOutput


class HookManager:
    """
    Manages registration and execution of hooks for an agent.

    The HookManager organizes hooks by type and executes them in priority order,
    stopping early when a hook returns a result.
    """

    def __init__(self, hooks: list[Hook] | None = None) -> None:
        """
        Initialize the hook manager.

        Args:
            hooks: Initial list of hooks to register
        """
        self._hooks: dict[EventType, list[Hook]] = defaultdict(list)

        if hooks:
            for hook in hooks:
                self.register(hook)

    def register(self, hook: Hook) -> None:
        """
        Register a hook.

        Hooks are organized by type and sorted by priority
        (lower numbers execute first).

        Args:
            hook: The hook to register
        """
        self._hooks[hook.event_type].append(hook)
        self._hooks[hook.event_type].sort(key=lambda h: h.priority)

    def get_hooks(self, event_type: EventType, tool_name: str | None) -> list[Hook]:
        """
        Get all hooks for a specific event type that match the tool name.

        Args:
            event_type: The type of event
            tool_name: Optional tool name to filter hooks. If None, returns all hooks for the event type.

        Returns:
            List of matching hooks, sorted by priority
        """
        hooks = self._hooks.get(event_type, [])

        if tool_name is None:
            return hooks

        return [hook for hook in hooks if hook.matches_tool(tool_name)]

    async def execute(self, event_type: EventType, hook_input: HookInput) -> HookOutput | None:
        """
        Execute all hooks for an event type in priority order.

        Stops at the first hook that returns a result.

        Args:
            event_type: The type of event
            hook_input: The input to pass to hooks

        Returns:
            The output from the first hook that returns a result, or None if no hooks return results
        """
        # Get tool_name from input if it has one (for tool hooks)
        tool_name = None
        if hasattr(hook_input, "tool_call"):
            tool_name = hook_input.tool_call.name

        hooks = self.get_hooks(event_type, tool_name)

        for hook in hooks:
            result = await hook.execute(hook_input)
            if result is not None:
                return result

        return None
