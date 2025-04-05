from abc import ABC, abstractmethod
from types import ModuleType, UnionType
from typing import ClassVar, Generic, TypeVar, get_args, get_origin

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion import enrichers
from ragbits.document_search.ingestion.enrichers.exceptions import EnricherElementNotSupportedError

ElementT = TypeVar("ElementT", bound=Element)


class ElementEnricher(Generic[ElementT], WithConstructionConfig, ABC):
    """
    Base class for element enrichers, responsible for providing additional information about elements.

    Enrichers operate on raw elements and are used to fill in missing fields that could not be filled in during parsing.
    They usually deal with summarizing text or describing images.
    """

    default_module: ClassVar[ModuleType | None] = enrichers
    configuration_key: ClassVar[str] = "enricher"

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
        Check if the enricher supports the element type.

        Args:
            element_type: The element type to validate against the enricher.

        Raises:
            EnricherElementNotSupportedError: If the element type is not supported.
        """
        expected_element_type = cls.__orig_bases__[0].__args__[0]  # type: ignore

        # Check if expected_element_type is a Union and if element_type is in that Union
        if (
            (origin := get_origin(expected_element_type))
            and origin == UnionType
            and element_type in get_args(expected_element_type)
        ):
            return

        # Check if element_type matches expected_element_type exactly
        if element_type == expected_element_type:
            return

        raise EnricherElementNotSupportedError(enricher_name=cls.__name__, element_type=element_type)
