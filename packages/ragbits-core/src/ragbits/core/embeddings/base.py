from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar, TypeVar

from ragbits.core import embeddings
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent

EmbeddingsOptionsT = TypeVar("EmbeddingsOptionsT", bound=Options)


class EmbeddingType(Enum):
    """
    Indicates the type of embedding in regard to what kind of data has been embedded.

    Used to specify the embedding type for a given element. Unlike `Element` type,
    which categorizes the element itself, `EmbeddingType` determines how the
    element's data is represented. For example, an image element can support
    multiple embedding types, such as a description, OCR output, or raw bytes,
    allowing for the creation of different embeddings for the same element.
    """

    TEXT = "text"
    IMAGE = "image"


class Embeddings(ConfigurableComponent[EmbeddingsOptionsT], ABC):
    """
    Abstract client for communication with embedding models.
    """

    options_cls: type[EmbeddingsOptionsT]
    default_module: ClassVar = embeddings
    configuration_key: ClassVar = "embedder"

    @abstractmethod
    async def embed_text(self, data: list[str], options: EmbeddingsOptionsT | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional settings used by the Embeddings model.

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

    async def embed_image(self, images: list[bytes], options: EmbeddingsOptionsT | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional settings used by the Embeddings model.

        Returns:
            List of embeddings for the given images.
        """
        raise NotImplementedError("Image embeddings are not supported by this model.")
