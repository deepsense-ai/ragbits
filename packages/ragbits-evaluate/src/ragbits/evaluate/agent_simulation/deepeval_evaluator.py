"""DeepEval integration for multi-turn conversation evaluation."""

from deepeval.metrics import (  # type: ignore[attr-defined]
    ConversationCompletenessMetric,
    ConversationRelevancyMetric,
    KnowledgeRetentionMetric,
)
from deepeval.test_case import ConversationalTestCase, LLMTestCase  # type: ignore[attr-defined]

from ragbits.evaluate.agent_simulation.models import Turn


class DeepEvalEvaluator:
    """Evaluator using DeepEval metrics for multi-turn conversations."""

    def __init__(self) -> None:
        """Initialize the DeepEval evaluator with multi-turn metrics."""
        self.completeness_metric = ConversationCompletenessMetric()
        self.knowledge_retention_metric = KnowledgeRetentionMetric()
        self.conversation_relevancy_metric = ConversationRelevancyMetric()

    @staticmethod
    def _evaluate_metric(
        metric: ConversationCompletenessMetric | KnowledgeRetentionMetric | ConversationRelevancyMetric,
        test_case: ConversationalTestCase,
    ) -> dict[str, float | str | None]:
        """Evaluate a single metric on a test case.

        Args:
            metric: The metric instance to evaluate
            test_case: The conversational test case to evaluate

        Returns:
            Dictionary containing score, reason, success, and optionally error
        """
        try:
            metric.measure(test_case)
            return {
                "score": metric.score,
                "reason": getattr(metric, "reason", None),
                "success": getattr(metric, "success", None),
            }
        except Exception as e:
            return {
                "score": None,
                "reason": None,
                "success": None,
                "error": str(e),
            }

    def _evaluate_all_metrics(self, test_case: ConversationalTestCase) -> dict[str, dict[str, float | str | None]]:
        """Evaluate all metrics on a test case.

        Args:
            test_case: The conversational test case to evaluate

        Returns:
            Dictionary containing evaluation results for each metric
        """
        results: dict[str, dict[str, float | str | None]] = {}

        results["ConversationCompletenessMetric"] = self._evaluate_metric(self.completeness_metric, test_case)

        results["KnowledgeRetentionMetric"] = self._evaluate_metric(self.knowledge_retention_metric, test_case)

        results["ConversationRelevancyMetric"] = self._evaluate_metric(self.conversation_relevancy_metric, test_case)

        return results

    def evaluate_conversation(self, turns: list[Turn]) -> dict[str, dict[str, float | str | None]]:
        """Evaluate a conversation using DeepEval metrics.

        Args:
            turns: List of conversation turns to evaluate

        Returns:
            Dictionary containing evaluation results for each metric
        """
        if not turns:
            return {}

        # Convert ragbits Turn objects to deepeval LLMTestCase objects
        deepeval_turns = []
        for turn in turns:
            # Each turn becomes an LLMTestCase where input is user message and actual_output is assistant response
            deepeval_turns.append(LLMTestCase(input=turn.user, actual_output=turn.assistant))

        # Create conversational test case
        test_case = ConversationalTestCase(turns=deepeval_turns)

        # Evaluate with each metric
        return self._evaluate_all_metrics(test_case)
