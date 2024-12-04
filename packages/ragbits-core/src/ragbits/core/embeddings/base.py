from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar

from ragbits.core import embeddings
from ragbits.core.utils.config_handling import WithConstructionConfig


class EmbeddingType(Enum):
    """
    Indicates the type of embedding in regard to what kind of data has been embedded.

    Used to specify the embedding type for a given element. Unlike `Element` type,
    which categorizes the element itself, `EmbeddingType` determines how the
    element's data is represented. For example, an image element can support
    multiple embedding types, such as a description, OCR output, or raw bytes,
    allowing for the creation of different embeddings for the same element.
    """

    TEXT: str = "text"
    IMAGE: str = "image"


class Embeddings(WithConstructionConfig, ABC):
    """
    Abstract client for communication with embedding models.
    """

    default_module: ClassVar = embeddings

    @abstractmethod
    async def embed_text(self, data: list[str]) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.

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

    async def embed_image(self, images: list[bytes]) -> list[list[float]]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.

        Returns:
            List of embeddings for the given images.
        """
        raise NotImplementedError("Image embeddings are not supported by this model.")
