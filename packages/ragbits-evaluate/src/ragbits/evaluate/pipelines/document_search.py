from typing import Any

from .base import EvaluationPipeline, EvaluationResult


class DocumentSearchEvaluationPipeline(EvaluationPipeline):
    """
    Document search evaluation pipeline.
    """

    async def __call__(self, data: dict[str, Any]) -> EvaluationResult:
        """
        Runs the document search evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
        return EvaluationResult()
