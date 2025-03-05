from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.options import Options, OptionsT


class NoopEmbedder(Embedder[Options]):
    """
    A no-op implementation of the Embedder class.

    This class provides a simple embedding method that returns a fixed
    embedding vector for each input text. It's mainly useful for testing
    or as a placeholder when an actual embedding model is not required.
    """

    options_cls = Options

    def __init__(
        self, default_options: OptionsT | None = None, return_values: list[list[list[float]]] | None = None
    ) -> None:
        """
        Constructs a new NoopEmbedder instance.

        Args:
            default_options: The default options for the component.
            return_values: The embeddings to return for text input. Each time the embed_text method is called,
                the next list of embeddings is returned, after being trimmed / repeated to match the number of inputs.
                After all return_values have been used, the cycle starts again. Default is a single vector of [0.1, 0.1]
        """
        super().__init__(default_options=default_options)
        self.return_values = return_values or [[[0.1, 0.1]]]
        self.return_cycle = 0

    @traceable
    async def embed_text(self, data: list[str], options: Options | None = None) -> list[list[float]]:  # noqa: PLR6301
        """
        Embeds a list of strings into a list of vectors.

        Args:
            data: A list of input text strings to embed.
            options: Additional settings used by the Embedder model.

        Returns:
            A list of embedding vectors, one for each input text.
        """
        # Get the right values for the current cycle
        values = self.return_values[self.return_cycle]

        # Expand the values to at least match the number of inputs
        values = values * (len(data) // len(values) + 1)

        # Update the cycle counter
        self.return_cycle = (self.return_cycle + 1) % len(self.return_values)

        return values[: len(data)]
