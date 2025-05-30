from collections.abc import Callable

from fastembed import SparseTextEmbedding

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import EmbedderOptionsT, SparseVector, VectorSize
from ragbits.core.embeddings.dense.fastembed import FastEmbedOptions
from ragbits.core.embeddings.sparse.base import SparseEmbedder


class FastEmbedSparseEmbedder(SparseEmbedder[FastEmbedOptions]):
    """
    Class for creating sparse text embeddings using FastEmbed library.
    For more information, see the [FastEmbed GitHub](https://github.com/qdrant/fastembed).
    """

    options_cls = FastEmbedOptions
    _model: SparseTextEmbedding

    def __init__(self, model_name: str, use_gpu: bool = False, default_options: FastEmbedOptions | None = None):
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self.use_gpu = use_gpu
        if use_gpu:
            self._model = SparseTextEmbedding(model_name=model_name, providers=["CUDAExecutionProvider"])
        else:
            self._model = SparseTextEmbedding(model_name=model_name)

    def __reduce__(self) -> tuple[Callable, tuple[str, bool, FastEmbedOptions | None]]:
        """
        Makes the FastEmbedSparseEmbedder class picklable by defining how it should be reconstructed.

        Returns:
            The tuple of function and its arguments that allows reconstruction of the FastEmbedSparseEmbedder.
        """
        return (self.__class__, (self.model_name, self.use_gpu, self.default_options))

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this FastEmbed sparse model.

        For sparse models, this returns the vocabulary size.

        Returns:
            VectorSize object with is_sparse=True and the vocabulary size.
        """
        # Get model info from FastEmbed's supported models list
        supported_models = self._model.list_supported_models()
        model_info = next((model for model in supported_models if model["model"] == self.model_name), None)

        if model_info and "vocab_size" in model_info:
            vocab_size = model_info["vocab_size"]
        else:
            sample_embedding = await self.embed_text(["sample text with various tokens"])
            vocab_size = (
                max(sample_embedding[0].indices) + 1 if sample_embedding and sample_embedding[0].indices else 30000
            )

        return VectorSize(size=vocab_size, is_sparse=True)

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
        with trace(
            data=data, model_name=self.model_name, model_obj=repr(self._model), options=merged_options.dict()
        ) as outputs:
            outputs.embeddings = [
                SparseVector(values=[float(x) for x in result.values], indices=[int(x) for x in result.indices])
                for result in self._model.embed(data, **merged_options.dict())
            ]
        return outputs.embeddings
