"""DeepEval metric collectors following the MetricCollector protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ragbits.evaluate.agent_simulation.metrics.collectors import MetricCollector

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.results import TurnResult


class DeepEvalCompletenessMetricCollector(MetricCollector):
    """Tracks conversation completeness using DeepEval's ConversationCompletenessMetric.

    Evaluates how well the assistant addresses the user's requests throughout
    the conversation.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[DeepEvalCompletenessMetricCollector]),
        ... )
        >>> print(result.metrics.custom.get("deepeval_completeness"))
    """

    def __init__(self) -> None:
        """Initialize the completeness metric collector."""
        self._turns: list[tuple[str, str]] = []  # (user, assistant) pairs

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """No-op for DeepEval completeness collector.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (stored in on_turn_end).
        """
        pass

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Record the turn for later evaluation.

        Args:
            turn_result: The result of the completed turn.
        """
        self._turns.append((turn_result.user_message, turn_result.assistant_message))

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Evaluate conversation completeness using DeepEval.

        Args:
            all_turns: List of all turn results.

        Returns:
            Dictionary with deepeval_completeness score and reason.
        """
        if not self._turns:
            return {}

        try:
            from deepeval.metrics import ConversationCompletenessMetric  # type: ignore[attr-defined]
            from deepeval.test_case import ConversationalTestCase, LLMTestCase  # type: ignore[attr-defined]

            deepeval_turns = [LLMTestCase(input=user, actual_output=assistant) for user, assistant in self._turns]
            test_case = ConversationalTestCase(turns=deepeval_turns)
            metric = ConversationCompletenessMetric()
            metric.measure(test_case)

            return {
                "deepeval_completeness": metric.score,
                "deepeval_completeness_reason": getattr(metric, "reason", None),
            }
        except Exception as e:
            return {
                "deepeval_completeness": None,
                "deepeval_completeness_error": str(e),
            }

    def reset(self) -> None:
        """Reset collector state for a new conversation."""
        self._turns = []


class DeepEvalRelevancyMetricCollector(MetricCollector):
    """Tracks conversation relevancy using DeepEval's ConversationRelevancyMetric.

    Evaluates how relevant the assistant's responses are to the user's queries.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[DeepEvalRelevancyMetricCollector]),
        ... )
        >>> print(result.metrics.custom.get("deepeval_relevancy"))
    """

    def __init__(self) -> None:
        """Initialize the relevancy metric collector."""
        self._turns: list[tuple[str, str]] = []

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """No-op for DeepEval relevancy collector.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (stored in on_turn_end).
        """
        pass

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Record the turn for later evaluation.

        Args:
            turn_result: The result of the completed turn.
        """
        self._turns.append((turn_result.user_message, turn_result.assistant_message))

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Evaluate conversation relevancy using DeepEval.

        Args:
            all_turns: List of all turn results.

        Returns:
            Dictionary with deepeval_relevancy score and reason.
        """
        if not self._turns:
            return {}

        try:
            from deepeval.metrics import ConversationRelevancyMetric  # type: ignore[attr-defined]
            from deepeval.test_case import ConversationalTestCase, LLMTestCase  # type: ignore[attr-defined]

            deepeval_turns = [LLMTestCase(input=user, actual_output=assistant) for user, assistant in self._turns]
            test_case = ConversationalTestCase(turns=deepeval_turns)
            metric = ConversationRelevancyMetric()
            metric.measure(test_case)

            return {
                "deepeval_relevancy": metric.score,
                "deepeval_relevancy_reason": getattr(metric, "reason", None),
            }
        except Exception as e:
            return {
                "deepeval_relevancy": None,
                "deepeval_relevancy_error": str(e),
            }

    def reset(self) -> None:
        """Reset collector state for a new conversation."""
        self._turns = []


class DeepEvalKnowledgeRetentionMetricCollector(MetricCollector):
    """Tracks knowledge retention using DeepEval's KnowledgeRetentionMetric.

    Evaluates how well the assistant retains and uses information from earlier
    in the conversation.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[DeepEvalKnowledgeRetentionMetricCollector]),
        ... )
        >>> print(result.metrics.custom.get("deepeval_knowledge_retention"))
    """

    def __init__(self) -> None:
        """Initialize the knowledge retention metric collector."""
        self._turns: list[tuple[str, str]] = []

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """No-op for DeepEval knowledge retention collector.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message (stored in on_turn_end).
        """
        pass

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Record the turn for later evaluation.

        Args:
            turn_result: The result of the completed turn.
        """
        self._turns.append((turn_result.user_message, turn_result.assistant_message))

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Evaluate knowledge retention using DeepEval.

        Args:
            all_turns: List of all turn results.

        Returns:
            Dictionary with deepeval_knowledge_retention score and reason.
        """
        if not self._turns:
            return {}

        try:
            from deepeval.metrics import KnowledgeRetentionMetric  # type: ignore[attr-defined]
            from deepeval.test_case import ConversationalTestCase, LLMTestCase  # type: ignore[attr-defined]

            deepeval_turns = [LLMTestCase(input=user, actual_output=assistant) for user, assistant in self._turns]
            test_case = ConversationalTestCase(turns=deepeval_turns)
            metric = KnowledgeRetentionMetric()
            metric.measure(test_case)

            return {
                "deepeval_knowledge_retention": metric.score,
                "deepeval_knowledge_retention_reason": getattr(metric, "reason", None),
            }
        except Exception as e:
            return {
                "deepeval_knowledge_retention": None,
                "deepeval_knowledge_retention_error": str(e),
            }

    def reset(self) -> None:
        """Reset collector state for a new conversation."""
        self._turns = []


class DeepEvalAllMetricsCollector(MetricCollector):
    """Composite collector that evaluates all DeepEval conversation metrics.

    Runs all three DeepEval metrics (completeness, relevancy, knowledge retention)
    at the end of the conversation.

    Example:
        >>> result = await run_simulation(
        ...     scenario=scenario,
        ...     chat=chat,
        ...     config=SimulationConfig(metrics=[DeepEvalAllMetricsCollector]),
        ... )
        >>> print(result.metrics.custom.get("deepeval_completeness"))
        >>> print(result.metrics.custom.get("deepeval_relevancy"))
        >>> print(result.metrics.custom.get("deepeval_knowledge_retention"))
    """

    def __init__(self) -> None:
        """Initialize the all-metrics collector."""
        self._completeness = DeepEvalCompletenessMetricCollector()
        self._relevancy = DeepEvalRelevancyMetricCollector()
        self._knowledge_retention = DeepEvalKnowledgeRetentionMetricCollector()

    def on_turn_start(self, turn_index: int, task_index: int, user_message: str) -> None:
        """Delegate to all child collectors.

        Args:
            turn_index: 1-based index of the current turn.
            task_index: 0-based index of the current task.
            user_message: The user message.
        """
        self._completeness.on_turn_start(turn_index, task_index, user_message)
        self._relevancy.on_turn_start(turn_index, task_index, user_message)
        self._knowledge_retention.on_turn_start(turn_index, task_index, user_message)

    def on_turn_end(self, turn_result: TurnResult) -> None:
        """Delegate to all child collectors.

        Args:
            turn_result: The result of the completed turn.
        """
        self._completeness.on_turn_end(turn_result)
        self._relevancy.on_turn_end(turn_result)
        self._knowledge_retention.on_turn_end(turn_result)

    def on_conversation_end(self, all_turns: list[TurnResult]) -> dict[str, Any]:
        """Aggregate metrics from all child collectors.

        Args:
            all_turns: List of all turn results.

        Returns:
            Dictionary combining all DeepEval metrics.
        """
        combined: dict[str, Any] = {}
        combined.update(self._completeness.on_conversation_end(all_turns))
        combined.update(self._relevancy.on_conversation_end(all_turns))
        combined.update(self._knowledge_retention.on_conversation_end(all_turns))
        return combined

    def reset(self) -> None:
        """Reset all child collectors."""
        self._completeness.reset()
        self._relevancy.reset()
        self._knowledge_retention.reset()
