from abc import ABC, abstractmethod
from typing import ClassVar

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.retrieval import rephrasers


class QueryRephraser(WithConstructionConfig, ABC):
    """
    Rephrases a query. Can provide multiple rephrased queries from one sentence / question.
    """

    default_module: ClassVar = rephrasers
    configuration_key: ClassVar = "rephraser"

    @abstractmethod
    async def rephrase(self, query: str) -> list[str]:
        """
        Rephrase a query.

        Args:
            query: The query to rephrase.

        Returns:
            The rephrased queries.
        """
