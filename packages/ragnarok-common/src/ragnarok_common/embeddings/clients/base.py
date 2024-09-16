from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Dict, Generic, TypeVar

from ...types import NotGiven

EmbeddingsClientOptions = TypeVar("EmbeddingsClientOptions", bound="EmbeddingsOptions")


@dataclass
class EmbeddingsOptions(ABC):
    """
    Abstract dataclass that represents all available encoder call options.
    """

    _not_given: ClassVar[Any] = None

    def dict(self) -> Dict[str, Any]:
        """
        Creates a dictionary representation of the EmbeddingsOptions instance.
        If a value is None, it will be replaced with a provider-specific not-given sentinel.

        Returns:
            A dictionary representation of the EmbeddingsOptions instance.
        """
        options = asdict(self)
        return {
            key: self._not_given if value is None or isinstance(value, NotGiven) else value
            for key, value in options.items()
        }


class EmbeddingsClient(Generic[EmbeddingsClientOptions], ABC):
    """
    Abstract client for a direct communication with encoder models.
    """

    def __init__(self, model_name: str) -> None:
        """
        Constructs a new EmbeddingsClient instance.

        Args:
            model_name: Name of the model to be used.
        """
        self.model_name = model_name

    @abstractmethod
    async def call(self, data: list[str], options: EmbeddingsClientOptions) -> list[list[float]]:
        """
        Calls encoder model inference API.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the Embeddings Client.

        Returns:
            List of embeddings for the given strings.
        """
