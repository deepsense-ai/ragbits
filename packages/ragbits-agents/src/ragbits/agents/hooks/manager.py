"""
Hook manager for organizing and executing hooks.

This module provides the HookManager class which handles registration,
organization, and execution of hooks during lifecycle events.
"""

import hashlib
import json
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Generic, Literal, overload

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import (
    EventType,
    OnEventCallback,
    PostRunCallback,
    PostToolCallback,
    PreRunCallback,
    PreToolCallback,
    StreamingEvent,
)
from ragbits.agents.tool import ToolReturn
from ragbits.core.llms.base import LLMClientOptionsT, ToolCall
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import AgentOptions, AgentResult, AgentRunContext

# Confirmation ID length: 16 hex chars provides sufficient uniqueness
# while being compact for display and storage
CONFIRMATION_ID_LENGTH = 16


class HookManager(Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]):
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

    @overload
    def get_hooks(
        self, event_type: Literal[EventType.PRE_TOOL], tool_name: str | None = ...
    ) -> list[Hook[PreToolCallback]]: ...

    @overload
    def get_hooks(
        self, event_type: Literal[EventType.POST_TOOL], tool_name: str | None = ...
    ) -> list[Hook[PostToolCallback]]: ...

    @overload
    def get_hooks(
        self, event_type: Literal[EventType.PRE_RUN], tool_name: str | None = ...
    ) -> list[Hook[PreRunCallback]]: ...

    @overload
    def get_hooks(
        self, event_type: Literal[EventType.POST_RUN], tool_name: str | None = ...
    ) -> list[Hook[PostRunCallback]]: ...

    @overload
    def get_hooks(
        self, event_type: Literal[EventType.ON_EVENT], tool_name: str | None = ...
    ) -> list[Hook[OnEventCallback]]: ...

    def get_hooks(self, event_type: EventType, tool_name: str | None = None) -> list[Hook]:
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
        context: "AgentRunContext",
    ) -> tuple[ToolCall, ConfirmationRequest | None]:
        """
        Execute pre-tool hooks with proper chaining.

        Each hook sees the modified ToolCall from the previous hook.
        Execution stops immediately if any hook returns "deny" or "ask" (unless confirmed).

        Args:
            tool_call: The tool call to process
            context: Agent run context containing tool_confirmations

        Returns:
            Tuple of (ToolCall with final arguments and decision, optional ConfirmationRequest)
        """
        current_tool_call = tool_call.model_copy()

        for hook in self.get_hooks(EventType.PRE_TOOL, tool_call.name):
            # Generate confirmation_id: hash(hook_function_name + tool_name + arguments)
            hook_name = hook.callback.__name__
            confirmation_id_str = (
                f"{hook_name}:{tool_call.name}:{json.dumps(current_tool_call.arguments, sort_keys=True)}"
            )
            confirmation_id = hashlib.sha256(confirmation_id_str.encode()).hexdigest()[:CONFIRMATION_ID_LENGTH]

            result: ToolCall = await hook.callback(current_tool_call)

            if result.decision in ("ask", "deny") and not result.reason:
                raise ValueError(f"reason is required when decision='{result.decision}'")

            if result.decision == "deny":
                return result, None

            elif result.decision == "ask":
                # Check if already confirmed/declined in context
                for conf in context.tool_confirmations:
                    if conf.get("confirmation_id") == confirmation_id:
                        if conf.get("confirmed"):
                            # Approved → convert to "pass" and continue to next hook
                            result = result.model_copy(update={"decision": "pass"})
                            break
                        else:
                            # Declined → convert to "deny" and stop immediately
                            return (
                                result.model_copy(
                                    update={
                                        "decision": "deny",
                                        "reason": "❌ Action declined by user",
                                    }
                                ),
                                None,
                            )
                else:
                    # Not in context → return "ask" with ConfirmationRequest
                    confirmation_request = ConfirmationRequest(
                        confirmation_id=confirmation_id,
                        tool_name=tool_call.name,
                        tool_description=result.reason,  # type: ignore[arg-type]  # guaranteed non-None by ValueError check above
                        arguments=current_tool_call.arguments,
                    )
                    return result, confirmation_request

            # Chain: next hook gets the returned ToolCall
            current_tool_call = result

        # All hooks passed — ensure decision is "pass"
        return current_tool_call.model_copy(update={"decision": "pass"}), None

    async def execute_post_tool(
        self,
        tool_call: ToolCall,
        tool_return: ToolReturn,
    ) -> ToolReturn:
        """
        Execute post-tool hooks with proper output chaining.

        Each hook sees the modified output from the previous hook.

        Args:
            tool_call: The tool call that was executed
            tool_return: Object representing the output of the tool (with value passed to the LLM and metadata)

        Returns:
            ToolReturn with final output
        """
        for hook in self.get_hooks(EventType.POST_TOOL, tool_call.name):
            tool_return = await hook.callback(tool_call, tool_return)

        return tool_return

    async def execute_pre_run(
        self,
        _input: PromptInputT | str | None,
        options: "AgentOptions[LLMClientOptionsT]",
        context: "AgentRunContext",
    ) -> PromptInputT | str | None:
        """
        Execute pre-run hooks with proper input chaining.

        Each hook sees the modified input from the previous hook.

        Args:
            _input: The input for the agent run
            options: The options for the agent run
            context: The context for the agent run

        Returns:
            The final (potentially modified) input
        """
        for hook in self.get_hooks(EventType.PRE_RUN):
            _input = await hook.callback(_input, options, context)

        return _input

    async def execute_post_run(
        self,
        result: "AgentResult[PromptOutputT]",
        options: "AgentOptions[LLMClientOptionsT]",
        context: "AgentRunContext",
    ) -> "AgentResult[PromptOutputT]":
        """
        Execute post-run hooks with proper result chaining.

        Each hook sees the modified result from the previous hook.

        Args:
            result: The result from the agent run
            options: The options for the agent run
            context: The context for the agent run

        Returns:
            The final (potentially modified) AgentResult
        """
        for hook in self.get_hooks(EventType.POST_RUN):
            result = await hook.callback(result, options, context)

        return result

    async def execute_on_event(
        self,
        generator: AsyncGenerator[StreamingEvent, None],
    ) -> AsyncGenerator[StreamingEvent, None]:
        """
        Process streaming events through ON_EVENT hooks.

        Hooks are composed as a pipeline of async generators: each hook wraps the previous
        generator, so events flow through the chain without intermediate collection.
        A hook callback can either:
        - Return an awaitable resolving to a StreamingEvent (pass-through / modify)
        - Return an awaitable resolving to None (suppress the event)
        - Return an async generator yielding multiple StreamingEvents (expand one event into many)

        Args:
            generator: The source async generator of streaming events

        Yields:
            Processed streaming events (potentially modified by hooks)
        """

        async def apply_hook_to_stream(
            source: AsyncGenerator[StreamingEvent, None],
            hook: Hook[OnEventCallback],
        ) -> AsyncGenerator[StreamingEvent, None]:
            """
            Apply a single ON_EVENT hook to every event from a source generator.
            """
            async for event in source:
                result = hook.callback(event)
                if isinstance(result, AsyncGenerator):
                    async for sub_event in result:
                        yield sub_event
                else:
                    awaited = await result
                    if awaited is not None:
                        yield awaited


        for hook in self.get_hooks(EventType.ON_EVENT):
            generator = apply_hook_to_stream(generator, hook)

        async for event in generator:
            yield event
