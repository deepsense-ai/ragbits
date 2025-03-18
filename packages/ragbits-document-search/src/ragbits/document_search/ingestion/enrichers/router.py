from collections.abc import Mapping
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig, import_by_path
from ragbits.document_search.documents import element
from ragbits.document_search.documents.element import IntermediateElement, IntermediateImageElement
from ragbits.document_search.ingestion.enrichers.base import BaseIntermediateHandler
from ragbits.document_search.ingestion.enrichers.images import ImageIntermediateHandler

_DEFAULT_ENRICHERS: dict[type[IntermediateElement], ImageIntermediateHandler] = {
    IntermediateImageElement: ImageIntermediateHandler(),
}


class ElementEnricherRouter(WithConstructionConfig):
    """
    The class responsible for routing the element to the correct enricher based on the element type.
    """

    configuration_key: ClassVar[str] = "enrichers"

    _enrichers: Mapping[type[IntermediateElement], ImageIntermediateHandler]

    def __init__(
        self,
        enrichers: Mapping[type[IntermediateElement], ImageIntermediateHandler] | None = None,
    ) -> None:
        """
        Initialize the ElementEnricherRouter instance.

        Args:
            enrichers: The mapping of element types and their enrichers. To override default enrichers.

        Example:
            {
                IntermediateImageElement: ImageIntermediateHandler(),
                IntermediateTextElement: TextIntermediateHandler(),
            }
        """
        self._enrichers = {**_DEFAULT_ENRICHERS, **enrichers} if enrichers else _DEFAULT_ENRICHERS

    @classmethod
    def from_config(cls, config: dict[str, ObjectContructionConfig]) -> Self:
        """
        Initialize the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            The ElementEnricherRouter.

        Raises:
            InvalidConfigError: If any of the provided parsers cannot be initialized.
        """
        enrichers = {
            import_by_path(element_type, element): BaseIntermediateHandler.subclass_from_config(enricher_config)
            for element_type, enricher_config in config.items()
        }
        return cls(enrichers=enrichers)  # type: ignore

    def get(self, element_type: type[IntermediateElement]) -> BaseIntermediateHandler:
        """
        Get the enricher for the element.

        Args:
            element_type: The element type.

        Returns:
            The enricher for processing the element.

        Raises:
            ValueError: If no enricher is found for the element type.
        """
        enricher = self._enrichers.get(element_type)

        if isinstance(enricher, BaseIntermediateHandler):
            return enricher

        raise ValueError(f"No enricher found for the element type {element_type}")
