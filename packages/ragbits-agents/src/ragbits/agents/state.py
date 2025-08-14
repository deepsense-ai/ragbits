import copy
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.core.types import NOT_GIVEN

StateT = TypeVar('StateT')

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, PromptInputT, PromptOutputT
    from ragbits.agents.tool import ToolChoice


class StatefulMixin:
    """Mixin class providing state management capabilities.
    """

    def update_state(self, updates: dict[str, Any] | object) -> None:
        """Update state with new values.

        Args:
            updates: Either a dictionary of updates to apply or a new state object.
        """
        if isinstance(updates, dict):
            # Apply dictionary updates to existing state object
            for key, value in updates.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        elif hasattr(updates, '__dict__'):
            for key, value in updates.__dict__.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    async def save_to_store_async(
        self,
        state_store: 'StateStore[Any]',
        session_id: str,
        auto_save: bool = True
    ) -> None:
        """Asynchronously save state to a state store.

        Args:
            state_store: The state store to save to.
            session_id: Session identifier for the state.
            auto_save: Whether to save automatically.
        """
        if (auto_save and
            state_store and
            session_id and
            hasattr(state_store, 'save_state')):
            await state_store.save_state(session_id, self)


class BaseState(BaseModel, StatefulMixin):
    """Base class for state objects."""
    pass



class StateStore(ABC, Generic[StateT]):
    """
    This interface defines the contract for storing and retrieving agent state
    across sessions.
    """

    @abstractmethod
    async def save_state(self, session_id: str, state: StateT) -> None:
        """Save state for a session.

        Args:
            session_id: Unique identifier for the session.
            state: State object to save.
        """

    @abstractmethod
    async def load_state(self, session_id: str) -> StateT | None:
        """Load state for a session.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            Loaded state object or None if not found.
        """

    @abstractmethod
    async def delete_state(self, session_id: str) -> None:
        """Delete state for a session.

        Args:
            session_id: Unique identifier for the session.
        """

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of all session identifiers in storage.
        """


class InMemoryStateStore(StateStore[StateT]):
    """Simple in-memory state store.
    """

    def __init__(self) -> None:
        """Initialize the in-memory state store."""
        self._states: dict[str, StateT] = {}

    async def save_state(self, session_id: str, state: StateT) -> None:
        """Save state in memory."""
        self._states[session_id] = copy.deepcopy(state)

    async def load_state(self, session_id: str) -> StateT | None:
        """Load state from memory."""
        state = self._states.get(session_id)
        if state is not None:
            return copy.deepcopy(state)
        return None

    async def delete_state(self, session_id: str) -> None:
        """Delete state from memory."""
        self._states.pop(session_id, None)

    async def list_sessions(self) -> list[str]:
        """List all session IDs in memory."""
        return list(self._states.keys())




async def run_with_state(
    agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
    input: "str | PromptInputT | None" = None,
    state_store: StateStore[StateT] | None = None,
    session_id: str = "default",
    initial_state: StateT | None = None,
    options: "AgentOptions[LLMClientOptionsT] | None" = None,
    tool_choice: "ToolChoice | None" = None,
    **kwargs: Any  # noqa: ANN401
) -> "AgentResult[PromptOutputT]":
    """Run agent with state management.

    Args:
        agent: The agent to run.
        input: Input for the agent run.
        state_store: State store for persistence (if None, uses in-memory storage).
        session_id: Unique session identifier for state persistence.
        initial_state: Initial state to use for new sessions.
        options: Agent run options.
        tool_choice: Tool choice parameter.
        **kwargs: Additional keyword arguments.

    Returns:
        Agent result with updated state context.
    """
    # Runtime import to avoid circular dependencies
    from ragbits.agents._main import AgentRunContext

    state = await state_store.load_state(session_id) if state_store else None
    if state is None and initial_state is not None:
        state = copy.deepcopy(initial_state)

    context = AgentRunContext[StateT](
        state=state,
        session_id=session_id,
        state_store=state_store
    )

    result = await agent.run(input, options, context, tool_choice, **kwargs)

    auto_save = True
    if options and options.auto_save is not NOT_GIVEN:
        auto_save = bool(options.auto_save)

    if auto_save and context.state is not None and state_store is not None:
        await state_store.save_state(session_id, context.state)

    return result
