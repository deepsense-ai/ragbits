from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from ragbits.core import embeddings
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent

EmbedderOptionsT = TypeVar("EmbedderOptionsT", bound=Options)


class Embedder(ConfigurableComponent[EmbedderOptionsT], ABC):
    """
    Abstract client for communication with embedding models.
    """

    options_cls: type[EmbedderOptionsT]
    default_module: ClassVar = embeddings
    configuration_key: ClassVar = "embedder"

    @abstractmethod
    async def embed_text(self, data: list[str], options: EmbedderOptionsT | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional settings used by the Embedder model.

        Returns:
            List of embeddings for the given strings.
        """

    def image_support(self) -> bool:  # noqa: PLR6301
        """
        Check if the model supports image embeddings.

        Returns:
            True if the model supports image embeddings, False otherwise.
        """
        return False

    async def embed_image(self, images: list[bytes], options: EmbedderOptionsT | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional settings used by the Embedder model.

        Returns:
            List of embeddings for the given images.
        """
        raise NotImplementedError("Image embeddings are not supported by this model.")
