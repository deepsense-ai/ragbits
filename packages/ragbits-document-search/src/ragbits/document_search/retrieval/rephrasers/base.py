import abc


class QueryRephraser(abc.ABC):
    """
    Rephrases a query. Can provide multiple rephrased queries from one sentence / question.
    """

    @staticmethod
    @abc.abstractmethod
    def rephrase(query: str) -> list[str]:
        """Rephrase a query.

        Args:
            query: The query to rephrase.

        Returns:
            The rephrased queries.
        """
