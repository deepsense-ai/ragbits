import inspect

from typing_extensions import Self

from ragbits.document_search.documents.element import Element


class EnricherError(Exception):
    """
    Class for all exceptions raised by the element enricher and router.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __reduce__(self) -> tuple[type[Self], tuple]:
        return self.__class__, tuple(
            self.__getattribute__(param_name)
            for param_name in list(inspect.signature(self.__class__.__init__).parameters)[1:]
        )


class EnricherNotFoundError(EnricherError):
    """
    Raised when no enricher was found for the element type.
    """

    def __init__(self, element_type: type[Element]) -> None:
        super().__init__(f"No enricher found for the element type {element_type}")
        self.element_type = element_type


class EnricherElementNotSupportedError(EnricherError):
    """
    Raised when the element type is not supported by the enricher.
    """

    def __init__(self, enricher_name: str, element_type: type[Element]) -> None:
        super().__init__(f"Element type {element_type} is not supported by the {enricher_name}")
        self.enricher_name = enricher_name
        self.element_type = element_type
