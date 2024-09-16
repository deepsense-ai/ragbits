from abc import ABC, abstractmethod
from functools import cached_property
from typing import Generic, Optional, Type

from .clients.base import EmbeddingsClient, EmbeddingsClientOptions


class Embeddings(Generic[EmbeddingsClientOptions], ABC):
    """
    Abstract client for communication with embedding models.
    """

    _options_cls: Type[EmbeddingsClientOptions]

    def __init__(self, model_name: str, default_options: Optional[EmbeddingsClientOptions] = None) -> None:
        """
        Constructs a new Embeddings instance.

        Args:
            model_name: Name of the model to be used.
            default_options: Default options to be used.
        """
        self.model_name = model_name
        self.default_options = default_options or self._options_cls()

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "_options_cls"):
            raise TypeError(f"Class {cls.__name__} is missing the '_options_cls' attribute")

    @cached_property
    @abstractmethod
    def client(self) -> EmbeddingsClient:
        """
        Client for embeddings.
        """

    async def embed_text(self, data: list[str], options: Optional[EmbeddingsClientOptions] = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional settings used by the embedding model.

        Returns:
            List of embeddings for the given strings.
        """

        options = options or self.default_options

        response = await self.client.call(data=data, options=options)

        return response
