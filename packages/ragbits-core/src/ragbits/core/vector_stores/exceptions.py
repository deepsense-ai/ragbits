class VectorStoreError(Exception):
    """
    Base class for all exceptions raised by the Vector Store.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

class VectorStoreConnectionError(VectorStoreError):
    """Raised when a connection to the vector store fails."""

    def __init__(self, message: str | None = None, original_error: Exception | None = None) -> None:
        """
        Initialize the error.

        Args:
            message: The error message. If None, a default message will be used.
            original_error: The original error that caused this connection error.
        """
        if message is None:
            message = "Failed to connect to vector store"
            if original_error is not None:
                message = f"{message}: {str(original_error)}"
        super().__init__(message)
        self.message = message


class VectorStoreOperationError(VectorStoreError):
    """Raised for general operation failures (e.g. add, remove, search)."""

    def __init__(self, message: str = "Operation failed in vector store.") -> None:
        super().__init__(message)
        self.message = message

class VectorStoreValidationError(VectorStoreError):
    """Raised when validation fails in the vector store."""

    def __init__(self, message: str = "Validation failed in vector store.") -> None:
        super().__init__(message)
        self.message = message

