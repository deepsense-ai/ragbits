from collections.abc import Mapping
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig, import_by_path
from ragbits.document_search.documents import element
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.enrichers.base import ElementEnricher
from ragbits.document_search.ingestion.enrichers.exceptions import EnricherNotFoundError

_DEFAULT_ENRICHERS: dict[type[Element], ElementEnricher] = {}


class ElementEnricherRouter(WithConstructionConfig):
    """
    The class responsible for routing the element to the correct enricher based on the element type.
    """

    configuration_key: ClassVar[str] = "enricher_router"

    _enrichers: Mapping[type[Element], ElementEnricher]

    def __init__(
        self,
        enrichers: Mapping[type[Element], ElementEnricher] | None = None,
    ) -> None:
        """
        Initialize the ElementEnricherRouter instance.

        Args:
            enrichers: The mapping of element types and their enrichers. To override default enrichers.
        """
        self._enrichers = {**_DEFAULT_ENRICHERS, **enrichers} if enrichers else _DEFAULT_ENRICHERS

    def __contains__(self, element_type: type[Element]) -> bool:
        """
        Check if there is an enricher defined of the given element type.

        Args:
            element_type: The element type.

        Returns:
            True if the enricher is defined for the element, otherwise False.
        """
        return element_type in self._enrichers

    @classmethod
    def from_config(cls, config: dict[str, ObjectConstructionConfig]) -> Self:
        """
        Initialize the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            The ElementEnricherRouter.

        Raises:
            InvalidConfigError: If any of the provided parsers cannot be initialized.
        """
        enrichers: dict[type[Element], ElementEnricher] = {
            import_by_path(element_type, element): ElementEnricher.subclass_from_config(enricher_config)
            for element_type, enricher_config in config.items()
        }
        return super().from_config({"enrichers": enrichers})

    def get(self, element_type: type[Element]) -> ElementEnricher:
        """
        Get the enricher for the element.

        Args:
            element_type: The element type.

        Returns:
            The enricher for processing the element.

        Raises:
            EnricherNotFoundError: If no enricher is found for the element type.
        """
        enricher = self._enrichers.get(element_type)

        if isinstance(enricher, ElementEnricher):
            return enricher

        raise EnricherNotFoundError(element_type)
