from abc import ABC, abstractmethod

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import Element


class ElementEnricher(WithConstructionConfig, ABC):
    """
    Base class for element enrichers, responsible for providing additional information about elements.
    """

    @abstractmethod
    async def enrich(self, elements: list[Element]) -> list[Element]:
        """
        Enrich elements.

        Args:
            elements: The elements to be enriched.

        Returns:
            The list of enriched elements.
        """
