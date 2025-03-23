from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.enrichers.exceptions import EnricherElementNotSupportedError

ElementT = TypeVar("ElementT", bound=Element)


class ElementEnricher(Generic[ElementT], WithConstructionConfig, ABC):
    """
    Base class for element enrichers, responsible for providing additional information about elements.
    """

    @abstractmethod
    async def enrich(self, elements: list[ElementT]) -> list[ElementT]:
        """
        Enrich elements.

        Args:
            elements: The elements to be enriched.

        Returns:
            The list of enriched elements.

        Raises:
            EnricherError: If the enrichment of the elements failed.
        """

    @classmethod
    def validate_element_type(cls, element_type: type[Element]) -> None:
        """
        Check if the enricher supports the enricher type.

        Args:
            element_type: The element type to validate against the enricher.

        Raises:
            EnricherElementNotSupportedError: If the element type is not supported.
        """
        if element_type != cls.__orig_bases__[0].__args__[0]:  # type: ignore
            raise EnricherElementNotSupportedError(enricher_name=cls.__name__, element_type=element_type)
