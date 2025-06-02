from dataclasses import field
from typing import Any

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.options import Options

try:
    from sentence_transformers import SentenceTransformer

    HAS_LOCAL_EMBEDDINGS = True
except ImportError:
    HAS_LOCAL_EMBEDDINGS = False


class LocalEmbedderOptions(Options):
    """
    Dataclass that represents available call options for the LocalEmbedder client.
    """

    encode_kwargs: dict = field(default_factory=dict)


class LocalEmbedder(DenseEmbedder[LocalEmbedderOptions]):
    """
    Class for interaction with any encoder available in HuggingFace.

    Note: Local implementation is not dedicated for production. Use it only in experiments / evaluation.
    """

    options_cls = LocalEmbedderOptions

    def __init__(
        self,
        model_name: str,
        default_options: LocalEmbedderOptions | None = None,
        **model_kwargs: Any,  # noqa: ANN401
    ) -> None:
        """
        Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use.
            default_options: Default options for the embedding model.
            model_kwargs: Additional arguments to pass to the SentenceTransformer.

        Raises:
            ImportError: If the 'local' extra requirements are not installed.
        """
        if not HAS_LOCAL_EMBEDDINGS:
            raise ImportError("You need to install the 'local' extra requirements to use local embeddings models")

        super().__init__(default_options=default_options)

        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name, **model_kwargs)

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this local SentenceTransformer model.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            sample_embedding = await self.embed_text(["sample"])
            dimension = len(sample_embedding[0])
        return VectorSize(size=dimension, is_sparse=False)

    async def embed_text(self, data: list[str], options: LocalEmbedderOptions | None = None) -> list[list[float]]:
        """
        Calls the appropriate encoder endpoint with the given data and options.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the embedding model.

        Returns:
            List of embeddings for the given strings.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            data=data,
            model_name=self.model_name,
            model_obj=repr(self.model),
            options=merged_options.dict(),
        ) as outputs:
            outputs.embeddings = self.model.encode(data, **merged_options.encode_kwargs).tolist()
        return outputs.embeddings
