from abc import ABC, abstractmethod
from typing import TypeVar

from ragbits.core.embeddings.base import Embedder, SparseVector
from ragbits.core.options import Options

SparseEmbedderOptionsT = TypeVar("SparseEmbedderOptionsT", bound=Options)


class SparseEmbedder(Embedder[SparseEmbedderOptionsT], ABC):
    """Sparse embedding interface"""

    @abstractmethod
    async def embed_text(self, texts: list[str], options: SparseEmbedderOptionsT | None = None) -> list[SparseVector]:
        """
        Transforms a list of texts into sparse vectors.

        Args:
            texts: list of input texts.
            options: optional embedding options

        Returns:
            list of sparse embeddings.
        """

    async def embed_image(
        self, images: list[bytes], options: SparseEmbedderOptionsT | None = None
    ) -> list[SparseVector]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional settings used by the Embedder model.

        Returns:
            List of sparse embeddings for the given images.
        """
        raise NotImplementedError("Image embeddings are not supported by this model.")
