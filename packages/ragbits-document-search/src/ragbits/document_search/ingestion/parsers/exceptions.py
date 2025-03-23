import inspect

from typing_extensions import Self

from ragbits.document_search.documents.document import DocumentType


class ParserError(Exception):
    """
    Class for all exceptions raised by the document parser and router.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __reduce__(self) -> tuple[type[Self], tuple]:
        return self.__class__, tuple(
            self.__getattribute__(param_name)
            for param_name in list(inspect.signature(self.__class__.__init__).parameters)[1:]
        )


class ParserNotFoundError(ParserError):
    """
    Raised when no parser was found for the document type.
    """

    def __init__(self, document_type: DocumentType) -> None:
        super().__init__(f"No parser found for the document type {document_type}")
        self.document_type = document_type


class ParserDocumentNotSupportedError(ParserError):
    """
    Raised when the document type is not supported by the parser.
    """

    def __init__(self, parser_name: str, document_type: DocumentType) -> None:
        super().__init__(f"Document type {document_type.value} is not supported by the {parser_name}")
        self.parser_name = parser_name
        self.document_type = document_type
