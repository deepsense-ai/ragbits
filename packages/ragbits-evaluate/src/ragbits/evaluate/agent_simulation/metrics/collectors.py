"""Base protocol and composite collector for metrics collection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ragbits.chat.interface.types import ChatResponseUnion

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.results import TurnResult


class MetricCollector(ABC):
    """Protocol for collecting metrics during conversation simulation.

    Implement this protocol to create custom metric collectors that can
    be passed to run_simulation(). Collectors receive callbacks at various
    points during the simulation lifecycle.

    Example:
        >>> class CustomCollector:
        ...     def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        ...         print(f"Turn {turn_index} starting")
        ...
        ...     def on_turn_end(self, turn_result: TurnResult) -> None:
        ...         print(f"Turn completed: {turn_result.task_completed}")
        ...
        ...     def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        ...         return {"total_turns_tracked": len(all_turns)}
        ...
        ...     def reset(self) -> None:
        ...         pass
    """

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:  # noqa: PLR6301
        """Called before agent processes a turn.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message being sent to the agent.
        """
        return

    def on_streamed_response(  # noqa: PLR6301
        self, turn_index: int, task_index: int, user_message: str, response: ChatResponseUnion
    ) -> None:
        """Called after receiving chunk from chat interface.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message being sent to the agent.
            response: Response yielded from chat, usually command or text chunk.
        """
        return

    def on_turn_end(self, turn_result: TurnResult) -> None:  # noqa: PLR6301
        """Called after a turn completes.

        Args:
            turn_result: The result of the completed turn.
        """
        return

    @abstractmethod
    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Called when the conversation ends, returns computed metrics.

        Args:
            all_turns: List of all turn results from the conversation.

        Returns:
            Dictionary of metric names to values.
        """


class CompositeMetricCollector:
    """Combines multiple metric collectors into a single interface.

    This collector delegates all method calls to its child collectors,
    aggregating their results at the end of the conversation.

    Example:
        >>> from ragbits.evaluate.agent_simulation.metrics import (
        ...     LatencyMetricCollector,
        ...     TokenUsageMetricCollector,
        ...     CompositeMetricCollector,
        ... )
        >>> composite = CompositeMetricCollector(
        ...     [
        ...         LatencyMetricCollector(),
        ...         TokenUsageMetricCollector(),
        ...     ]
        ... )
    """

    def __init__(self, collectors: list[MetricCollector] | None = None) -> None:
        """Initialize with a list of metric collectors.

        Args:
            collectors: List of collectors to combine. Defaults to empty list.
        """
        self._collectors: list[MetricCollector] = collectors or []

    def add(self, collector: MetricCollector) -> None:
        """Add a collector to the composite.

        Args:
            collector: Collector to add.
        """
        self._collectors.append(collector)

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """Delegate to all child collectors.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message being sent to the agent.
        """
        for collector in self._collectors:
            collector.on_turn_start(turn_index, task_index, user_message)

    def on_streamed_response(
        self, turn_index: int, task_index: int, user_message: str, response: ChatResponseUnion
    ) -> None:
        """Delegate to all child collectors.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message being sent to the agent.
            response: Response yielded from chat, usually command or text chunk.
        """
        for collector in self._collectors:
            collector.on_streamed_response(turn_index, task_index, user_message, response)

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Delegate to all child collectors.

        Args:
            turn_result: The result of the completed turn.
        """
        for collector in self._collectors:
            collector.on_turn_end(turn_result)

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Aggregate metrics from all child collectors.

        Args:
            all_turns: List of all turn results from the conversation.

        Returns:
            Dictionary combining all collector metrics.
        """
        combined: dict[str, Any] = {}
        for collector in self._collectors:
            metrics = collector.on_conversation_end(all_turns)
            combined.update(metrics)
        return combined
