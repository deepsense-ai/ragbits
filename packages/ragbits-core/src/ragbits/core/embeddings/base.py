from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from pydantic import BaseModel

from ragbits.core import embeddings
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent

EmbedderOptionsT = TypeVar("EmbedderOptionsT", bound=Options)


class SparseVector(BaseModel):
    """Sparse Vector representation"""

    indices: list[int]
    values: list[float]

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            raise ValueError("There should be the same number of non-zero values as non-zero positions")

    def __repr__(self) -> str:
        return f"SparseVector(indices={self.indices}, values={self.values})"


class VectorSize(BaseModel):
    """Information about vector dimensions returned by an embedder"""

    size: int
    """The size/dimension of the vector"""

    is_sparse: bool = False
    """Whether this represents a sparse vector (where size is vocabulary size) or dense vector"""


class Embedder(ConfigurableComponent[EmbedderOptionsT], ABC):
    """
    Abstract class that defines a common interface for both sparse and dense embedding models.
    """

    options_cls: type[EmbedderOptionsT]
    default_module: ClassVar = embeddings
    configuration_key: ClassVar = "embedder"

    @abstractmethod
    async def embed_text(
        self, data: list[str], options: EmbedderOptionsT | None = None
    ) -> list[list[float]] | list[SparseVector]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional settings used by the Embedder model.

        Returns:
            List of embeddings for the given strings.
        """

    @abstractmethod
    async def get_vector_size(self) -> VectorSize:
        """
        Get information about the vector size/dimensions returned by this embedder.

        Returns:
            VectorSize object containing dimension information and whether vectors are sparse.
        """

    def image_support(self) -> bool:  # noqa: PLR6301
        """
        Check if the model supports image embeddings.

        Returns:
            True if the model supports image embeddings, False otherwise.
        """
        return False

    async def embed_image(
        self, images: list[bytes], options: EmbedderOptionsT | None = None
    ) -> list[list[float]] | list[SparseVector]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional settings used by the Embedder model.

        Returns:
            List of embeddings for the given images.
        """
        raise NotImplementedError("Image embeddings are not supported by this model.")
