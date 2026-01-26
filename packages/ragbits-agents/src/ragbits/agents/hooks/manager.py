"""
Hook manager for organizing and executing hooks.

This module provides the HookManager class which handles registration,
organization, and execution of hooks during lifecycle events.
"""

import hashlib
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Literal

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, PostToolInput, PostToolOutput, PreToolInput, PreToolOutput
from ragbits.core.llms.base import ToolCall

if TYPE_CHECKING:
    from ragbits.agents._main import AgentRunContext


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
        context: "AgentRunContext | None" = None,
    ) -> PreToolOutput:
        """
        Execute pre-tool hooks with proper chaining.

        Each hook sees the modified arguments from the previous hook.
        Execution stops immediately if any hook returns "deny" or "ask" (unless confirmed).

        Args:
            tool_call: The tool call to process
            context: Agent run context containing confirmed_hooks

        Returns:
            PreToolOutput with final arguments and decision
        """
        hooks = self.get_hooks(EventType.PRE_TOOL, tool_call.name)

        # Start with original arguments
        current_arguments = tool_call.arguments
        final_decision: Literal["pass", "ask", "deny"] = "pass"
        final_reason: str | None = None

        for hook in hooks:
            # Create input with current state (chained from previous hook)
            hook_input = PreToolInput(
                tool_call=tool_call.model_copy(update={"arguments": current_arguments}),
            )

            result: PreToolOutput = await hook.execute(hook_input)

            # Stop immediately on deny
            if result.decision == "deny":
                return result

            # Handle "ask" decision
            if result.decision == "ask":
                # Generate confirmation_id: hash(hook_function_name + tool_name + arguments)
                hook_name = hook.callback.__name__
                confirmation_str = f"{hook_name}:{tool_call.name}:{json.dumps(current_arguments, sort_keys=True)}"
                confirmation_id = hashlib.sha256(confirmation_str.encode()).hexdigest()[:16]

                # Check if already confirmed/declined in context
                if context and context.confirmed_hooks:
                    for conf in context.confirmed_hooks:
                        if conf.get("confirmation_id") == confirmation_id:
                            if conf.get("confirmed"):
                                # Approved → convert to "pass" and continue to next hook
                                result = PreToolOutput(arguments=current_arguments, decision="pass")
                            else:
                                # Declined → convert to "deny" and stop immediately
                                return PreToolOutput(
                                    arguments=current_arguments,
                                    decision="deny",
                                    reason=result.reason or "Hook declined by user",
                                )
                            break
                    else:
                        # Not in context → return "ask" with confirmation_id
                        return PreToolOutput(
                            arguments=current_arguments,
                            decision="ask",
                            reason=result.reason,
                            confirmation_id=confirmation_id,
                        )
                else:
                    # No context → return "ask" with confirmation_id
                    return PreToolOutput(
                        arguments=current_arguments,
                        decision="ask",
                        reason=result.reason,
                        confirmation_id=confirmation_id,
                    )

            # Chain arguments for next hook
            current_arguments = result.arguments

            # Track non-pass decisions
            if result.decision != "pass":
                final_decision = result.decision
                final_reason = result.reason

        # Return final chained result
        return PreToolOutput(
            arguments=current_arguments,
            decision=final_decision,
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
