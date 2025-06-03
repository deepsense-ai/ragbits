from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.options import Options, OptionsT


class NoopEmbedder(DenseEmbedder[Options]):
    """
    A no-op implementation of the Embedder class.

    This class provides a simple embedding method that returns a fixed
    embedding vector for each input text. It's mainly useful for testing
    or as a placeholder when an actual embedding model is not required.
    """

    options_cls = Options

    def __init__(
        self,
        default_options: OptionsT | None = None,
        return_values: list[list[list[float]]] | None = None,
        image_return_values: list[list[list[float]]] | None = None,
    ) -> None:
        """
        Constructs a new NoopEmbedder instance.

        Args:
            default_options: The default options for the component.
            return_values: The embeddings to return for text input. Each time the embed_text method is called,
                the next list of embeddings is returned, after being trimmed / repeated to match the number of inputs.
                After all return_values have been used, the cycle starts again. Default is a single vector of [0.1, 0.1]
            image_return_values: The embeddings to return for image input. Similar to return_values, but for images.
                If not provided, image embeddings are not supported.
        """
        super().__init__(default_options=default_options)
        self.return_values = return_values or [[[0.1, 0.1]]]
        self.image_return_values = image_return_values
        self.return_cycle = 0
        self.image_return_cycle = 0

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this NoopEmbedder.

        Returns:
            VectorSize object with the dimension of the first embedding vector.
        """
        return VectorSize(size=len(self.return_values[0][0]), is_sparse=False)

    async def embed_text(self, data: list[str], options: Options | None = None) -> list[list[float]]:  # noqa: PLR6301
        """
        Embeds a list of strings into a list of vectors.

        Args:
            data: A list of input text strings to embed.
            options: Additional settings used by the Embedder model.

        Returns:
            A list of embedding vectors, one for each input text.
        """
        with trace(
            data=data,
            options=self.default_options.dict(),
            return_values=self.return_values,
            return_cycle=self.return_cycle,
        ) as outputs:
            # Get the right values for the current cycle
            values = self.return_values[self.return_cycle]

            # Expand the values to at least match the number of inputs
            values = values * (len(data) // len(values) + 1)

            # Update the cycle counter
            self.return_cycle = (self.return_cycle + 1) % len(self.return_values)
            outputs.embeddings = values[: len(data)]
        return outputs.embeddings

    def image_support(self) -> bool:
        """
        Check if the model supports image embeddings, which is the case if image_return_values is provided.

        Returns:
            True if the model supports image embeddings, False otherwise.
        """
        return self.image_return_values is not None

    async def embed_image(self, images: list[bytes], options: Options | None = None) -> list[list[float]]:
        """
        Embeds a list of images into a list of vectors.

        Args:
            images: A list of input image bytes to embed.
            options: Additional settings used by the Embedder model.

        Returns:
            A list of embedding vectors, one for each input image.
        """
        if self.image_return_values is None:
            raise NotImplementedError("Image embeddings are not supported by this model.")
        with trace(
            images=self.image_return_values,
            options=self.default_options.dict(),
            image_return_values=self.image_return_values,
            image_return_cycle=self.image_return_cycle,
        ) as outputs:
            values = self.image_return_values[self.image_return_cycle]
            values = values * (len(images) // len(values) + 1)
            self.image_return_cycle = (self.image_return_cycle + 1) % len(self.image_return_values)
            outputs.embeddings = values[: len(images)]
        return outputs.embeddings
