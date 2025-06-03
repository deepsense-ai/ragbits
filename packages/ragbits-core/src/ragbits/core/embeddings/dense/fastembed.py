from collections.abc import Callable

from fastembed import TextEmbedding

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.base import DenseEmbedder, EmbedderOptionsT
from ragbits.core.options import Options


class FastEmbedOptions(Options):
    """
    Dataclass that represents available call options for the LocalEmbedder client.
    """

    batch_size: int = 256
    parallel: int | None = None


class FastEmbedEmbedder(DenseEmbedder[FastEmbedOptions]):
    """
    Class for creating dense text embeddings using FastEmbed library.
    For more information, see the [FastEmbed GitHub](https://github.com/qdrant/fastembed).
    """

    options_cls = FastEmbedOptions
    _model: TextEmbedding

    def __init__(self, model_name: str, use_gpu: bool = False, default_options: FastEmbedOptions | None = None):
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self.use_gpu = use_gpu
        if use_gpu:
            self._model = TextEmbedding(model_name=model_name, providers=["CUDAExecutionProvider"])
        else:
            self._model = TextEmbedding(model_name=model_name)

    def __reduce__(self) -> tuple[Callable, tuple[str, bool, FastEmbedOptions | None]]:
        """
        Makes the FastEmbedEmbedder class picklable by defining how it should be reconstructed.

        Returns:
            The tuple of function and its arguments that allows reconstruction of the FastEmbedEmbedder.
        """
        return (self.__class__, (self.model_name, self.use_gpu, self.default_options))

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this FastEmbed model.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        # Get model info from FastEmbed's supported models list
        supported_models = self._model.list_supported_models()
        model_info = next((model for model in supported_models if model["model"] == self.model_name), None)

        if model_info and "dim" in model_info:
            vector_size = model_info["dim"]
        else:
            # Fallback to the original method if metadata is not available
            sample_embedding = await self.embed_text(["sample"])
            vector_size = len(sample_embedding[0])

        return VectorSize(size=vector_size, is_sparse=False)

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
        with trace(
            data=data, model_name=self.model_name, model_obj=repr(self._model), options=merged_options.dict()
        ) as outputs:
            embeddings = [[float(x) for x in result] for result in self._model.embed(data, **merged_options.dict())]
            outputs.embeddings = embeddings
        return embeddings
