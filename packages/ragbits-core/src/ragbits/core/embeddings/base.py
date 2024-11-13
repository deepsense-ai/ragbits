from abc import ABC, abstractmethod


class Embeddings(ABC):
    """
    Abstract client for communication with embedding models.
    """

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
