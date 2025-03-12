from abc import ABC, abstractmethod

from ragbits.document_search.documents.element import Element, IntermediateElement


class BaseIntermediateHandler(ABC):
    """
    Base class for handling `IntermediateElement` processing.

    Implementations of this class should define how to transform an `IntermediateElement`
    into a fully processed `Element` using the `process` method.
    """

    @abstractmethod
    async def process(self, intermediate_element: IntermediateElement) -> Element:
        """
        Process an `IntermediateElement` and return a corresponding `Element`.

        Args:
            intermediate_element: The intermediate element to be processed.

        Returns:
            The processed `Element` corresponding to the given `IntermediateElement`.
        """
