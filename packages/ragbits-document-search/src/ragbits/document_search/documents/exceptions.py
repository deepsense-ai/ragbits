import inspect
from typing import Any


class SourceError(Exception):
    """
    Class for all exceptions raised by the document source.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __reduce__(self) -> tuple[type["SourceError"], tuple[Any, ...]]:
        # This __reduce__ method is written in a way that it automatically handles any subclass of SourceError.
        # It requires the subclass to have an initializer that store the arguments in the instance's state,
        # under the same name.
        init_params = inspect.signature(self.__class__.__init__).parameters

        args = [
            self.__getattribute__(param_name)
            for param_name in list(init_params.keys())[1:]  # Skip 'self'
        ]

        return self.__class__, tuple(args)


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


class WebDownloadError(SourceError):
    """
    Raised when an error occurs during the download of a file from an Web source.
    """

    def __init__(self, url: str, code: int):
        super().__init__(f"Download of {url} failed with code {code}.")
        self.url = url
        self.code = code
