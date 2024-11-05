class SourceError(Exception):
    """
    Class for all exceptions raised by the document source.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SourceConnectionError(SourceError):
    """
    Raised when there is an error connecting to the document source.
    """

    def __init__(self) -> None:
        super().__init__("Connection error.")


class SourceNotFoundError(SourceError):
    """
    Raised when the document is not found.
    """

    def __init__(self, source_id: str) -> None:
        super().__init__(f"Source with ID {source_id} not found.")
        self.source_id = source_id
