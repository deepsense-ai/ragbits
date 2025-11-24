"""DeepEval integration for multi-turn conversation evaluation."""

from __future__ import annotations

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
        results: dict[str, dict[str, float | str | None]] = {}

        # ConversationCompletenessMetric
        try:
            self.completeness_metric.measure(test_case)
            results["ConversationCompletenessMetric"] = {
                "score": self.completeness_metric.score,
                "reason": getattr(self.completeness_metric, "reason", None),
                "success": getattr(self.completeness_metric, "success", None),
            }
        except Exception as e:
            results["ConversationCompletenessMetric"] = {
                "score": None,
                "reason": None,
                "success": None,
                "error": str(e),
            }

        # KnowledgeRetentionMetric
        try:
            self.knowledge_retention_metric.measure(test_case)
            results["KnowledgeRetentionMetric"] = {
                "score": self.knowledge_retention_metric.score,
                "reason": getattr(self.knowledge_retention_metric, "reason", None),
                "success": getattr(self.knowledge_retention_metric, "success", None),
            }
        except Exception as e:
            results["KnowledgeRetentionMetric"] = {
                "score": None,
                "reason": None,
                "success": None,
                "error": str(e),
            }

        # ConversationRelevancyMetric
        try:
            self.conversation_relevancy_metric.measure(test_case)
            results["ConversationRelevancyMetric"] = {
                "score": self.conversation_relevancy_metric.score,
                "reason": getattr(self.conversation_relevancy_metric, "reason", None),
                "success": getattr(self.conversation_relevancy_metric, "success", None),
            }
        except Exception as e:
            results["ConversationRelevancyMetric"] = {
                "score": None,
                "reason": None,
                "success": None,
                "error": str(e),
            }

        return results
