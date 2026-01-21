"""
Hook manager for organizing and executing tool hooks.

This module provides the HookManager class which handles registration,
organization, and execution of hooks during tool lifecycle events.
"""

import logging
from collections import defaultdict

from ragbits.agents.hooks.base import EventType, ToolHook
from ragbits.agents.hooks.inputs import PostToolInput, PreToolInput
from ragbits.agents.hooks.outputs import PostToolOutput, PreToolOutput

logger = logging.getLogger(__name__)


class HookManager:
    """
    Manages registration and execution of tool hooks for an agent.

    The HookManager organizes hooks by type and executes them in priority order,
    stopping early when a hook returns a decision.
    """

    def __init__(self, hooks: list[ToolHook] | None = None) -> None:
        """
        Initialize the hook manager.

        Args:
            hooks: Initial list of hooks to register
        """
        self._hooks: dict[EventType, list[ToolHook]] = defaultdict(list)

        if hooks:
            for hook in hooks:
                self.register(hook)

    def register(self, hook: ToolHook) -> None:
        """
        Register a hook.

        Hooks are organized by type and sorted by priority
        (lower numbers execute first).

        Args:
            hook: The hook to register
        """
        self._hooks[hook.event_type].append(hook)
        # Sort by priority (lower numbers first)
        self._hooks[hook.event_type].sort(key=lambda h: h.priority) # TODO: Check if this is efficient

    def register_all(self, hooks: list[ToolHook]) -> None:
        """
        Register multiple hooks at once.

        Args:
            hooks: List of hooks to register
        """
        for hook in hooks:
            self.register(hook)

    def get_hooks(self, event_type: EventType, tool_name: str) -> list[ToolHook]:
        """
        Get all hooks for a specific type that match the tool name.

        Args:
            event_type: The type of event to get hooks for
            tool_name: The tool name to filter hooks

        Returns:
            List of hooks sorted by priority
        """
        hooks = self._hooks.get(event_type, [])
        return [h for h in hooks if h.matches_tool(tool_name)]

    async def execute_pre_tool(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict,
        context: Any,  # AgentRunContext
    ) -> PreToolOutput | None:
        """
        Execute pre-tool hooks for a tool invocation.

        Hooks are executed in priority order (lower priority first).
        Execution stops when a hook returns a decision (deny or modify).

        Args:
            tool_use_id: Unique identifier for this tool invocation
            tool_name: Name of the tool being invoked
            tool_input: Arguments being passed to the tool
            context: The agent run context

        Returns:
            PreToolOutput with the action to take, or None to proceed normally
        """
        hooks = self.get_hooks(EventType.PRE_TOOL, tool_name)

        if not hooks:
            return None

        # Create input for hooks
        hook_input = PreToolInput(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
        )

        # Execute hooks in priority order, stopping at first decision
        for hook in hooks:
            try:
                result = await hook.execute(hook_input)

                if result is not None:
                    # Hook returned a decision - stop and return it
                    logger.debug(
                        f"Pre-tool hook '{hook.name or 'unnamed'}' returned action: {result.action}"
                    )
                    return result

            except Exception as e:
                # Log error but continue with other hooks
                logger.error(
                    f"Error executing pre-tool hook '{hook.name or 'unnamed'}' for tool '{tool_name}': {e}",
                    exc_info=True,
                )
                continue

        # No hook returned a decision - allow by default
        return None

    async def execute_post_tool(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict,
        tool_output: "Any",
        error: Exception | None,
        context: "Any",  # AgentRunContext
    ) -> PostToolOutput | None:
        """
        Execute post-tool hooks after a tool completes.

        Hooks are executed in priority order (lower priority first).
        Execution stops when a hook returns a modification.

        Args:
            tool_use_id: Unique identifier for this tool invocation
            tool_name: Name of the tool that was invoked
            tool_input: Arguments that were passed to the tool
            tool_output: The result returned by the tool (None if error)
            error: Any error that occurred (None if successful)
            context: The agent run context

        Returns:
            PostToolOutput with the action to take, or None to pass through
        """
        hooks = self.get_hooks(EventType.POST_TOOL, tool_name)

        if not hooks:
            return None

        # Create input for hooks
        hook_input = PostToolInput(
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            error=error,
            context=context,
        )

        # Execute hooks in priority order, stopping at first modification
        for hook in hooks:
            try:
                result = await hook.execute(hook_input)

                if result is not None and result.action == "modify":
                    # Hook returned a modification - stop and return it
                    logger.debug(
                        f"Post-tool hook '{hook.name or 'unnamed'}' modified output for tool '{tool_name}'"
                    )
                    return result

            except Exception as e:
                # Log error but continue with other hooks
                logger.error(
                    f"Error executing post-tool hook '{hook.name or 'unnamed'}' for tool '{tool_name}': {e}",
                    exc_info=True,
                )
                continue

        # No hook modified the output - pass through
        return None

    def has_hooks(self, event_type: EventType, tool_name: str | None = None) -> bool:
        """
        Check if there are any registered hooks for an event type and optional tool.

        Args:
            event_type: The type of event to check
            tool_name: Optional tool name to filter hooks

        Returns:
            True if there are registered hooks, False otherwise
        """
        if tool_name is None:
            return len(self._hooks.get(event_type, [])) > 0
        return len(self.get_hooks(event_type, tool_name)) > 0

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()

    def count(self, event_type: EventType | None = None) -> int:
        """
        Count the number of registered hooks.

        Args:
            event_type: Optional event type to count hooks for.
                        If None, counts all hooks.

        Returns:
            Number of registered hooks
        """
        if event_type is None:
            return sum(len(hooks) for hooks in self._hooks.values())
        return len(self._hooks.get(event_type, []))
