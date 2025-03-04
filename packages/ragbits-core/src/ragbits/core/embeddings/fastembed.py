from fastembed import SparseTextEmbedding, TextEmbedding

from ragbits.core.audit import traceable
from ragbits.core.embeddings import Embedder, EmbedderOptionsT, SparseEmbedder
from ragbits.core.embeddings.sparse import SparseVector
from ragbits.core.options import Options


class FastEmbedOptions(Options):
    """
    Dataclass that represents available call options for the LocalEmbedder client.
    """

    batch_size: int = 256
    parallel: int | None = None


class FastEmbedEmbedder(Embedder[FastEmbedOptions]):
    """
    Class for creating dense text embeddings using FastEmbed library.
    For more information, see the [FastEmbed GitHub](https://github.com/qdrant/fastembed).
    """

    options_cls = FastEmbedOptions
    _model: TextEmbedding

    def __init__(self, model_name: str, default_options: FastEmbedOptions | None = None):
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self._model = TextEmbedding(model_name)

    @traceable
    async def embed_text(self, data: list[str], options: EmbedderOptionsT | None = None) -> list[list[float]]:
        """
        Embeds a list of strings into a list of embeddings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the embedding model.

        Returns:
            List of embeddings for the given strings.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        return [[float(x) for x in result] for result in self._model.embed(data, **merged_options.dict())]


class FastEmbedSparseEmbedder(SparseEmbedder[FastEmbedOptions]):
    """
    Class for creating sparse text embeddings using FastEmbed library.
    For more information, see the [FastEmbed GitHub](https://github.com/qdrant/fastembed).
    """

    options_cls = FastEmbedOptions
    _model: SparseTextEmbedding

    def __init__(self, model_name: str, default_options: FastEmbedOptions | None = None):
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self._model = SparseTextEmbedding(model_name)

    @traceable
    async def embed_text(self, data: list[str], options: EmbedderOptionsT | None = None) -> list[SparseVector]:
        """
        Embeds a list of strings into a list of sparse embeddings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the embedding model.

        Returns:
            List of embeddings for the given strings.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        return [
            SparseVector(values=[float(x) for x in result.values], indices=[int(x) for x in result.indices])
            for result in self._model.embed(data, **merged_options.dict())
        ]
