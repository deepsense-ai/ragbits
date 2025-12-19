"""Tracing utilities for agent simulation.

Provides context managers and analyzers for capturing and analyzing
LLM calls, tool invocations, and token usage during simulation runs.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import Token
from dataclasses import dataclass
from typing import Any

from ragbits.agents.tool import ToolCallResult
from ragbits.core.audit.traces import MemoryTraceHandler, set_trace_handlers
from ragbits.core.audit.traces.memory import TraceSpan, _TraceSession, _current_session
from ragbits.core.llms import Usage
from ragbits.core.llms.base import UsageItem

__all__ = [
    "LLMCall",
    "MemoryTraceHandler",
    "TraceAnalyzer",
    "TraceSpan",
    "collect_traces",
]


@dataclass
class LLMCall:
    """Represents a single LLM call extracted from traces."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float | None = None


@contextmanager
def collect_traces(simulation_id: str | None = None) -> Iterator[MemoryTraceHandler]:
    """Context manager for collecting traces during a simulation.

    Sets up a context-local trace session and registers a MemoryTraceHandler
    to capture all traced operations within the context.

    Args:
        simulation_id: Optional identifier for the simulation run.

    Yields:
        MemoryTraceHandler instance that captures traces for this context.

    Example:
        with collect_traces(simulation_id="sim-123") as handler:
            # Run simulation code here
            traces = handler.get_traces()
    """
    # Create a new session for this context
    session = _TraceSession()
    token: Token[_TraceSession | None] = _current_session.set(session)

    # Create and register the handler
    handler = MemoryTraceHandler()
    set_trace_handlers(handler)

    try:
        yield handler
    finally:
        # Restore previous session state
        _current_session.reset(token)


class TraceAnalyzer:
    """Analyzes trace spans to extract tool calls and usage information.

    This class processes trace data collected by MemoryTraceHandler to
    provide structured access to tool invocations and token usage metrics.
    """

    def __init__(self, traces: list[dict[str, Any]]) -> None:
        """Initialize the analyzer with trace data.

        Args:
            traces: List of trace span dictionaries from MemoryTraceHandler.get_traces().
        """
        self._traces = traces
        self._spans = [TraceSpan.from_dict(t) for t in traces]

    @classmethod
    def from_traces(cls, traces: list[dict[str, Any]]) -> "TraceAnalyzer":
        """Create an analyzer from trace dictionaries.

        Args:
            traces: List of trace span dictionaries.

        Returns:
            A new TraceAnalyzer instance.
        """
        return cls(traces)

    def get_tool_calls(self) -> list[ToolCallResult]:
        """Extract all tool call results from the traces.

        Searches through all spans (including nested children) for tool
        invocation traces and extracts the tool call information.

        Returns:
            List of ToolCallResult objects representing all tool calls.
        """
        tool_calls: list[ToolCallResult] = []
        self._extract_tool_calls_recursive(self._spans, tool_calls)
        return tool_calls

    def _extract_tool_calls_recursive(
        self, spans: list[TraceSpan], results: list[ToolCallResult]
    ) -> None:
        """Recursively extract tool calls from spans and their children.

        Args:
            spans: List of spans to process.
            results: List to append found tool calls to.
        """
        for span in spans:
            # Check if this span represents a tool call
            if self._is_tool_call_span(span):
                tool_result = self._extract_tool_call(span)
                if tool_result:
                    results.append(tool_result)

            # Recurse into children
            if span.children:
                self._extract_tool_calls_recursive(span.children, results)

    def _is_tool_call_span(self, span: TraceSpan) -> bool:
        """Check if a span represents a tool call.

        Args:
            span: The span to check.

        Returns:
            True if the span is a tool call, False otherwise.
        """
        # Tool calls typically have names like "Tool.call" or contain tool-related info
        name = span.name.lower()
        return "tool" in name and ("call" in name or "execute" in name or "invoke" in name)

    def _extract_tool_call(self, span: TraceSpan) -> ToolCallResult | None:
        """Extract a ToolCallResult from a tool call span.

        Args:
            span: The tool call span.

        Returns:
            ToolCallResult if extraction succeeds, None otherwise.
        """
        inputs = span.inputs
        outputs = span.outputs

        # Try to extract tool call info from span data
        tool_name = inputs.get("name", inputs.get("tool_name", span.name))
        tool_id = inputs.get("id", inputs.get("tool_id", ""))
        arguments = inputs.get("arguments", inputs.get("args", {}))
        result = outputs.get("result", outputs.get("returned", None))

        if isinstance(tool_name, str):
            return ToolCallResult(
                id=str(tool_id) if tool_id else "",
                name=tool_name,
                arguments=arguments if isinstance(arguments, dict) else {},
                result=result,
            )
        return None

    def get_usage(self) -> Usage:
        """Extract aggregated token usage from the traces.

        Searches through all spans for LLM call traces and aggregates
        the token usage information.

        Returns:
            Usage object with aggregated token usage across all LLM calls.
        """
        usage_items: list[UsageItem] = []
        self._extract_usage_recursive(self._spans, usage_items)
        return Usage(requests=usage_items)

    def _extract_usage_recursive(
        self, spans: list[TraceSpan], results: list[UsageItem]
    ) -> None:
        """Recursively extract usage info from spans and their children.

        Args:
            spans: List of spans to process.
            results: List to append found usage items to.
        """
        for span in spans:
            # Check if this span has usage information
            usage_item = self._extract_usage_from_span(span)
            if usage_item:
                results.append(usage_item)

            # Recurse into children
            if span.children:
                self._extract_usage_recursive(span.children, results)

    def _extract_usage_from_span(self, span: TraceSpan) -> UsageItem | None:
        """Extract a UsageItem from a span if it contains usage data.

        Args:
            span: The span to extract usage from.

        Returns:
            UsageItem if extraction succeeds, None otherwise.
        """
        outputs = span.outputs

        # Check for usage in outputs
        usage_data = outputs.get("usage", None)
        if isinstance(usage_data, dict):
            return UsageItem(
                model=usage_data.get("model", "unknown"),
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                estimated_cost=usage_data.get("estimated_cost", 0.0),
            )

        # Check for direct token counts in outputs
        if "prompt_tokens" in outputs or "completion_tokens" in outputs:
            return UsageItem(
                model=outputs.get("model", span.inputs.get("model", "unknown")),
                prompt_tokens=outputs.get("prompt_tokens", 0),
                completion_tokens=outputs.get("completion_tokens", 0),
                total_tokens=outputs.get("total_tokens", 0),
                estimated_cost=outputs.get("estimated_cost", 0.0),
            )

        return None
