from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embeddings


class NoopEmbeddings(Embeddings):
    """
    A no-op implementation of the Embeddings class.

    This class provides a simple embedding method that returns a fixed
    embedding vector for each input text. It's mainly useful for testing
    or as a placeholder when an actual embedding model is not required.
    """

    @traceable
    async def embed_text(self, data: list[str]) -> list[list[float]]:  # noqa: PLR6301
        """
        Embeds a list of strings into a list of vectors.

        Args:
            data: A list of input text strings to embed.

        Returns:
            A list of embedding vectors, where each vector
            is a fixed value of [0.1, 0.1] for each input string.
        """
        return [[0.1, 0.1]] * len(data)
