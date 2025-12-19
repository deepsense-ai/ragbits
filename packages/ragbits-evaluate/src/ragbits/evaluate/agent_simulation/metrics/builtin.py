"""Built-in metric collectors for common simulation metrics."""

from __future__ import annotations

import time
from functools import reduce
from typing import TYPE_CHECKING, Any

from ragbits.chat.interface.types import ChatResponseUnion, TextResponse
from ragbits.core.llms.base import Usage
from ragbits.evaluate.agent_simulation.metrics.collectors import MetricCollector

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.results import TurnResult


class LatencyMetricCollector(MetricCollector):
    """Tracks response latency per turn.

    Measures the wall-clock time from turn start to turn end,
    providing average, min, max, and per-turn latency metrics.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[LatencyMetricCollector]),
        ... )
        >>> print(result.metrics.custom["latency_avg_ms"])
    """

    def __init__(self) -> None:
        """Initialize the latency collector."""
        self._turn_start: float | None = None
        self._latencies: list[float] = []
        self._times_to_first_token: dict[int, float] = {}

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """Record the start time for this turn.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (unused).
        """
        self._turn_start = time.perf_counter()

    def on_streamed_response(
        self, turn_index: int, task_index: int, user_message: str, response: ChatResponseUnion
    ) -> None:
        """Record time to first token on first text response.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (unused).
            response: Response chunk from chat interface.
        """
        if turn_index not in self._times_to_first_token and isinstance(response, TextResponse):
            self._times_to_first_token[turn_index] = (time.perf_counter() - self._turn_start) * 1000

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Calculate and store the latency for this turn.

        Args:
            turn_result: The result of the completed turn (unused directly).
        """
        if self._turn_start is not None:
            latency_ms = (time.perf_counter() - self._turn_start) * 1000
            self._latencies.append(latency_ms)
            self._turn_start = None

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Return latency metrics.

        Args:
            all_turns: List of all turn results (unused).

        Returns:
            Dictionary with latency_avg_ms, latency_max_ms, latency_min_ms,
            and latency_per_turn_ms.
        """
        ttfts = list(self._times_to_first_token.values())

        rv = {}
        if self._latencies:
            rv.update(
                {
                    "latency_avg_ms": sum(self._latencies) / len(self._latencies),
                    "latency_max_ms": max(self._latencies),
                    "latency_min_ms": min(self._latencies),
                }
            )
        if ttfts:
            rv.update(
                {
                    "time_to_first_token_avg_ms": sum(ttfts) / len(ttfts),
                    "time_to_first_token_max_ms": max(ttfts),
                    "time_to_first_token_min_ms": min(ttfts),
                }
            )

        return rv


class TokenUsageMetricCollector(MetricCollector):
    """Tracks token usage and estimated cost per turn.

    Aggregates token counts from each turn to provide total and
    per-turn token usage statistics.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[TokenUsageMetricCollector]),
        ... )
        >>> print(result.metrics.custom["tokens_total"])
    """

    def __init__(self) -> None:
        """Initialize the token usage collector."""
        self._usage: dict[int, Usage] = {}

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """No-op for token collector.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (unused).
        """
        pass

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Record token usage from the turn result.

        Args:
            turn_result: The result of the completed turn.
        """
        self._usage[turn_result.turn_index] = turn_result.token_usage

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Return aggregated token usage metrics.

        Args:
            all_turns: List of all turn results (unused).

        Returns:
            Dictionary with tokens_total, tokens_prompt, tokens_completion,
            tokens_avg_per_turn, and estimated_usd.
        """
        if not self._usage:
            return {}

        total_usage = reduce(lambda a, b: a + b, self._usage.values())

        return {
            "tokens_total": total_usage.total_tokens,
            "tokens_prompt": total_usage.prompt_tokens,
            "tokens_completion": total_usage.completion_tokens,
            "tokens_avg_per_turn": total_usage.total_tokens / len(self._usage),
            "estimated_usd": total_usage.estimated_cost,
        }


class ToolUsageMetricCollector(MetricCollector):
    """Tracks tool call patterns during the conversation.

    Records which tools were called, how often, and on which turns,
    providing insights into agent behavior.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[ToolUsageMetricCollector]),
        ... )
        >>> print(result.metrics.custom["tools_unique"])
    """

    def __init__(self) -> None:
        """Initialize the tool usage collector."""
        self._tool_calls: list[list[str]] = []  # tool names per turn
        self._tool_counts: dict[str, int] = {}  # total count per tool

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """No-op for tool usage collector.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (unused).
        """
        pass

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Record tool calls from the turn result.

        Args:
            turn_result: The result of the completed turn.
        """
        tool_names: list[str] = []
        if turn_result.tool_calls:
            for tc in turn_result.tool_calls:
                name = tc.get("name", "unknown")
                tool_names.append(name)
                self._tool_counts[name] = self._tool_counts.get(name, 0) + 1

        self._tool_calls.append(tool_names)

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Return tool usage metrics.

        Args:
            all_turns: List of all turn results (unused).

        Returns:
            Dictionary with tools_total_calls, tools_unique, tools_counts,
            tools_per_turn, and turns_with_tools.
        """
        total_calls = sum(len(tools) for tools in self._tool_calls)
        turns_with_tools = sum(1 for tools in self._tool_calls if tools)

        return {
            "tools_total_calls": total_calls,
            "tools_unique": list(self._tool_counts.keys()),
            "tools_counts": self._tool_counts.copy(),
            "tools_per_turn": self._tool_calls.copy(),
            "turns_with_tools": turns_with_tools,
        }
