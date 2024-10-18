from typing import Any, Optional

from omegaconf import DictConfig

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


class DocumentSearchPrecision(Metric[DocumentSearchResult]):
    """
    Precision measures the accuracy of the retrieved documents. It is the ratio of the number of relevant
    documents retrieved to the total number of documents retrieved.

    Precision = Total Number of Relevent Documents Retrieved / Total Number of Documents Retrieved

    Precision evaluates: "Out of all the documents that the system retrieved, how many were actually relevant?”
    """

    def compute(self, results: list[DocumentSearchResult]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        total_relevant_documents_retrieved = sum(
            len(set(result.reference_passages) & set(result.predicted_passages)) for result in results
        )
        total_documents_retrieved = sum(len(set(result.predicted_passages)) for result in results)

        return {
            "DOCUMENT_SEARCH/PRECISION": (total_relevant_documents_retrieved / total_documents_retrieved)
            if total_documents_retrieved > 0
            else 0.0,
        }


class DocumentSearchRecall(Metric[DocumentSearchResult]):
    """
    Recall measures the comprehensiveness of the retrieved documents. It is the ratio of the number of relevant
    documents retrieved to the total number of relevant documents in the database for the given query.

    Recall = Total Number of Relevant Documents Retrieved / Total Number of Relevant Documents in the Database

    Recall evaluates: "Out of all the relevant documents that exist in the database,
    how many did the system manage to retrieve?"
    """

    def compute(self, results: list[DocumentSearchResult]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        total_relevant_documents_retrieved = sum(
            len(set(result.reference_passages) & set(result.predicted_passages)) for result in results
        )
        total_relevant_documents = sum(len(set(result.reference_passages)) for result in results)

        return {
            "DOCUMENT_SEARCH/RECALL": (total_relevant_documents_retrieved / total_relevant_documents)
            if total_relevant_documents > 0
            else 0.0,
        }


class DocumentSearchF1(Metric[DocumentSearchResult]):
    """
    F1 Score is the harmonic mean of precision and recall. It is the weighted average of Precision and Recall.

    F1 = 2 * (Precision * Recall) / (Precision + Recall)
    """

    def __init__(self, config: Optional[DictConfig] = None) -> None:
        """
        Initializes the metric.

        Args:
            config: The metric configuration.
        """
        super().__init__(config)
        self.precision = DocumentSearchPrecision(config)
        self.recall = DocumentSearchRecall(config)

    def compute(self, results: list[DocumentSearchResult]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        precision = self.precision.compute(results)["DOCUMENT_SEARCH/PRECISION"]
        recall = self.recall.compute(results)["DOCUMENT_SEARCH/RECALL"]

        return {
            "DOCUMENT_SEARCH/F1": (2 * (precision * recall) / (precision + recall))
            if (precision + recall) > 0
            else 0.0,
        }
