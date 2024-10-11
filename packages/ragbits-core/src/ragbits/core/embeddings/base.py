from abc import ABC, abstractmethod


class Embeddings(ABC):
    """
    Abstract client for communication with embedding models.
    """

    @abstractmethod
    async def embed_text(self, data: list[str]) -> list[list[float]]:
        """Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.

        Returns:
            List of embeddings for the given strings.
        """
