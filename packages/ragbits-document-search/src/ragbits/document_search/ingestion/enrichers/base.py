from abc import ABC, abstractmethod

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import Element


class BaseIntermediateHandler(WithConstructionConfig, ABC):
    """
    Base class for handling `IntermediateElement` processing.

    Implementations of this class should define how to transform an `IntermediateElement`
    into a fully processed `Element` using the `process` method.
    """

    @abstractmethod
    async def process(self, elements: list[Element]) -> list[Element]:
        """
        Process an `IntermediateElement` and return a corresponding `Element`.

        Args:
            elements: The elements to be enriched.

        Returns:
            The list of enriched elements.
        """
