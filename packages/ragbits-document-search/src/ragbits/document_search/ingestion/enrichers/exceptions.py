from ragbits.document_search.documents.element import Element


class EnricherError(Exception):
    """
    Class for all exceptions raised by the element enricher and router.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
