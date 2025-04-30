from pathlib import Path


class DataLoaderError(Exception):
    """
    Class for all exceptions raised by the data loader.
    """

    def __init__(self, message: str, data_path: Path) -> None:
        super().__init__(message)
        self.message = message
        self.data_path = data_path


class DataLoaderIncorrectFormatDataError(DataLoaderError):
    """
    Raised when the data are incorrectly formatted.
    """

    def __init__(self, required_features: list[str], data_path: Path) -> None:
        super().__init__(
            message=f"Dataset {data_path} is incorrectly formatted. Required features: {required_features}",
            data_path=data_path,
        )
        self.required_features = required_features
