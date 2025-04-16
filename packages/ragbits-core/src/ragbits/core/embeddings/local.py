from collections.abc import Iterator
from dataclasses import field
from typing import Any

from ragbits.core.audit import trace
from ragbits.core.embeddings import Embedder
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

    batch_size: int = 1
    model_init_kwargs: dict[str, Any] = field(default_factory=dict)
    encode_kwargs: dict[str, Any] = field(default_factory=dict)


class LocalEmbedder(Embedder[LocalEmbedderOptions]):
    """
    Class for interaction with any encoder available in HuggingFace.

    Note: Local implementation is not dedicated for production. Use it only in experiments / evaluation
    """

    options_cls = LocalEmbedderOptions

    def __init__(
        self,
        model_name: str,
        default_options: LocalEmbedderOptions | None = None,
    ) -> None:
        """Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use.
            default_options: Default options for the embedding model.

        Raises:
            ImportError: If the 'local' extra requirements are not installed.
        """
        if not HAS_LOCAL_EMBEDDINGS:
            raise ImportError("You need to install the 'local' extra requirements to use local embeddings models")

        super().__init__(default_options=default_options)

        self.model_name = model_name

        init_kwargs = {}
        if default_options and default_options.model_init_kwargs:
            init_kwargs = default_options.model_init_kwargs

        # Initialize the model with all provided parameters
        self.model = SentenceTransformer(self.model_name, **init_kwargs)

    async def embed_text(self, data: list[str], options: LocalEmbedderOptions | None = None) -> list[list[float]]:
        """Calls the appropriate encoder endpoint with the given data and options.

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
            embeddings = [
                [float(x) for x in result] for result in self.model.encode(data, **merged_options.encode_kwargs)
            ]
            outputs.embeddings = embeddings
        return embeddings

    @staticmethod
    def _batch(data: list[str], batch_size: int) -> Iterator[list[str]]:
        length = len(data)
        for ndx in range(0, length, batch_size):
            yield data[ndx : min(ndx + batch_size, length)]
