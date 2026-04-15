"""Base protocol and composite collector for metrics collection."""

from __future__ import annotations

import re
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

    Naming convention for class names: ``<Source><Name>MetricCollector``.
    The ``get_display_info()`` classmethod auto-derives display names by stripping
    the ``MetricCollector`` suffix and splitting CamelCase. If the module defines
    a ``METRIC_SOURCE`` constant, it's automatically picked up as the source label
    (shown as a badge in the UI) and stripped from the display name.

    To add metrics from a new library, create a module and define ``METRIC_SOURCE``::

        # metrics/ragas.py
        METRIC_SOURCE = "Ragas"


        class RagasAnswerRelevancyMetricCollector(MetricCollector):
            # source is auto-set to "Ragas", display name becomes "Answer Relevancy"
            ...

    Examples:
        - ``DeepEvalCompletenessMetricCollector`` (METRIC_SOURCE="DeepEval") → source="DeepEval", name="Completeness"
        - ``CustomLatencyMetricCollector`` (no METRIC_SOURCE) → source="", name="Custom Latency"
        - ``AccuracyMetricCollector`` (no METRIC_SOURCE) → source="", name="Accuracy"
    """

    source: str = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Auto-set source from module-level METRIC_SOURCE if not explicitly set on this class
        if "source" not in cls.__dict__:
            import sys

            module = sys.modules.get(cls.__module__)
            if module and hasattr(module, "METRIC_SOURCE"):
                cls.source = module.METRIC_SOURCE

    @classmethod
    def get_display_info(cls) -> dict[str, str]:
        """Return display metadata for the UI, derived from the class name and docstring.

        The name is auto-derived by stripping ``MetricCollector`` suffix and splitting
        CamelCase. If ``source`` is set, it's stripped from the start of the display name.
        The description is taken from the first non-empty paragraph of the class docstring
        (everything up to the first blank line), stripped of indentation.

        Returns:
            Dict with 'id', 'label', 'source', 'name', and 'description' keys.
        """
        cls_name = cls.__name__
        # Strip suffix and source prefix, then split CamelCase
        display = cls_name.replace("MetricCollector", "").replace("Metric", "")
        source = cls.source
        if source and display.startswith(source):
            display = display[len(source) :]
        words = re.findall(r"[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z])|[A-Z]+$", display)
        name = " ".join(words) if words else display

        label = f"{source} {name}".strip() if source else name

        # Extract a user-facing description from the docstring.
        #
        # Google-style docstrings follow this structure:
        #   Line 1: One-line summary (often just restates the class name — not useful)
        #   <blank>
        #   Detailed description paragraph(s) ← this is what we want to show
        #   <blank>
        #   Example:/Args:/Returns: sections (excluded)
        #
        # Strategy: use inspect.getdoc() (correctly dedents docstrings where the
        # first line is unindented), collect paragraphs, skip the first (summary),
        # and concatenate the rest up to the first section header. Fall back to
        # the summary only if no detailed description exists.
        import inspect

        description = ""
        doc = inspect.getdoc(cls)
        if doc:
            # Known Google-style section headers — stop collecting when we hit one
            section_headers = {
                "args", "arguments", "returns", "return", "yields", "yield",
                "raises", "except", "example", "examples", "note", "notes",
                "warning", "warnings", "see also", "attributes", "references",
            }
            paragraphs: list[str] = []
            current: list[str] = []
            done = False
            for line in doc.split("\n"):
                stripped = line.strip()
                # Section header: e.g. "Args:", "Example:" — ends the body
                if stripped.endswith(":") and stripped[:-1].strip().lower() in section_headers:
                    done = True
                    break
                if not stripped:
                    if current:
                        paragraphs.append(" ".join(current))
                        current = []
                    continue
                current.append(stripped)
            if current and not done:
                paragraphs.append(" ".join(current))
            elif current:
                paragraphs.append(" ".join(current))

            # Prefer detailed description (paragraphs after the summary)
            if len(paragraphs) > 1:
                description = " ".join(paragraphs[1:])
            elif paragraphs:
                description = paragraphs[0]

        return {"id": cls_name, "label": label, "source": source, "name": name, "description": description}

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
