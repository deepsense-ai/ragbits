from abc import ABC, abstractmethod


class QueryRephraser(ABC):
    """
    Rephrases a query. Can provide multiple rephrased queries from one sentence / question.
    """

    @abstractmethod
    async def rephrase(self, query: str) -> list[str]:
        """
        Rephrase a query.

        Args:
            query: The query to rephrase.

        Returns:
            The rephrased queries.
        """

    @classmethod
    def from_config(cls, config: dict) -> "QueryRephraser":
        """
        Create an instance of `QueryRephraser` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the rephraser.

        Returns:
            An instance of the rephraser class initialized with the provided configuration.
        """
        return cls(**config)
