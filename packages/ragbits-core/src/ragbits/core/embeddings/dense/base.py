from abc import ABC, abstractmethod

from ragbits.core.embeddings.base import Embedder, EmbedderOptionsT


class DenseEmbedder(Embedder[EmbedderOptionsT], ABC):  # noqa: F821
    """
    Abstract client for communication with dense embedding models.
    """

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
