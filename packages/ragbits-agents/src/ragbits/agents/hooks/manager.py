"""
Hook manager for organizing and executing hooks.

This module provides the HookManager class which handles registration,
organization, and execution of hooks during lifecycle events.
"""

from collections import defaultdict
from typing import Any

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, PostToolInput, PostToolOutput, PreToolInput, PreToolOutput
from ragbits.core.llms.base import ToolCall


class HookManager:
    """
    Manages registration and execution of hooks for an agent.

    The HookManager organizes hooks by type and executes them in priority order,
    with proper chaining of modifications between hooks.
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

    async def execute_pre_tool(
        self,
        tool_call: ToolCall,
    ) -> PreToolOutput:
        """
        Execute pre-tool hooks with proper chaining.

        Each hook sees the modified arguments from the previous hook.
        Execution stops immediately if any hook returns "deny".

        Args:
            tool_call: The tool call to process

        Returns:
            PreToolOutput with final arguments and decision
        """
        hooks = self.get_hooks(EventType.PRE_TOOL, tool_call.name)

        # Start with original arguments
        current_arguments = tool_call.arguments
        final_reason: str | None = None

        for hook in hooks:
            # Create input with current state (chained from previous hook)
            hook_input = PreToolInput(
                tool_call=tool_call.model_copy(update={"arguments": current_arguments}),
            )

            result: PreToolOutput = await hook.execute(hook_input)

            # Stop immediately on deny
            if result.decision in ("deny", "ask"):
                return result

            # Chain arguments for next hook
            current_arguments = result.arguments

        return PreToolOutput(
            arguments=current_arguments,
            decision="pass",
            reason=final_reason,
        )

    async def execute_post_tool(
        self,
        tool_call: ToolCall,
        output: Any,  # noqa: ANN401
        error: Exception | None,
    ) -> PostToolOutput:
        """
        Execute post-tool hooks with proper output chaining.

        Each hook sees the modified output from the previous hook.

        Args:
            tool_call: The tool call that was executed
            output: The tool output
            error: Any error that occurred

        Returns:
            PostToolOutput with final output
        """
        hooks = self.get_hooks(EventType.POST_TOOL, tool_call.name)

        # Start with original output
        current_output = output

        for hook in hooks:
            # Create input with current state (chained from previous hook)
            hook_input = PostToolInput(
                tool_call=tool_call,
                output=current_output,
                error=error,
            )

            result: PostToolOutput = await hook.execute(hook_input)

            # Chain output for next hook
            current_output = result.output

        # Return final chained result
        return PostToolOutput(output=current_output)
