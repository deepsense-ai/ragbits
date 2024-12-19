from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embeddings
from ragbits.core.options import Options


class NoopEmbeddings(Embeddings[Options]):
    """
    A no-op implementation of the Embeddings class.

    This class provides a simple embedding method that returns a fixed
    embedding vector for each input text. It's mainly useful for testing
    or as a placeholder when an actual embedding model is not required.
    """

    options_cls = Options

    @traceable
    async def embed_text(self, data: list[str], options: Options | None = None) -> list[list[float]]:  # noqa: PLR6301
        """
        Embeds a list of strings into a list of vectors.

        Args:
            data: A list of input text strings to embed.
            options: Additional settings used by the Embeddings model.

        Returns:
            A list of embedding vectors, where each vector
            is a fixed value of [0.1, 0.1] for each input string.
        """
        return [[0.1, 0.1]] * len(data)
