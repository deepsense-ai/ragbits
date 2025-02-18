from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import ClassVar, TypeVar

import numpy as np
import tiktoken

from ragbits.core import embeddings
from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent

SparseEmbeddingsOptionsT = TypeVar("SparseEmbeddingsOptionsT", bound=Options)


@dataclass
class SparseVector:
    """Sparse Vector representation"""

    non_zero_dims: list[int]
    non_zero_vals: list[int]
    dim: int

    def __post_init__(self) -> None:
        if len(self.non_zero_dims) != len(self.non_zero_vals):
            raise ValueError("There should be the same number of non-zero values as non-zero positions")
        if any(dim >= self.dim or dim < 0 for dim in self.non_zero_dims):
            raise ValueError("Indexes should be in the range of the vector dim")

    def __repr__(self) -> str:
        return f"SparseVector(non_zero_dims={self.non_zero_dims}, non_zero_vals={self.non_zero_vals}, dim={self.dim})"


class SparseEmbeddings(ConfigurableComponent[SparseEmbeddingsOptionsT], ABC):
    """Sparse embedding interface"""

    options_cls: type[SparseEmbeddingsOptionsT]
    default_module: ClassVar = embeddings
    configuration_key: ClassVar = "sparse_embedder"

    @abstractmethod
    def embed_text(self, texts: list[str]) -> list[SparseVector]:
        """Transforms a list of texts into sparse vectors"""


class BagOfTokensOptions(Options):
    """A dataclass with definition of BOT options"""

    get_from_model_name: bool | None | NotGiven = NOT_GIVEN
    min_token_count: int | None | NotGiven = NOT_GIVEN


class BagOfTokens(SparseEmbeddings[BagOfTokensOptions]):
    """BagofTokens implementations of sparse Embeddings interface"""

    options_cls = BagOfTokensOptions

    def __init__(self, encoding_or_model_name: str, default_options: BagOfTokensOptions | None = None):
        """
        Initializes the BagOfTokens embedding
        Args:
            encoding_name: Name of encoding to be used. Needs to be supported by tiktoken library.
        """
        super().__init__(default_options=default_options)
        self.encoder = (
            tiktoken.get_encoding(encoding_name=encoding_or_model_name)
            if not self.default_options.get_from_model_name
            else tiktoken.encoding_for_model(model_name=encoding_or_model_name)
        )
        self.dim = self.encoder.n_vocab

    def embed_text(self, texts: list[str]) -> list[SparseVector]:
        """
        Transforms a list of texts into sparse vectors using bag-of-tokens representation.

        Args:
            texts: list of input texts.

        Returns:
            list of SparseVector instances.
        """
        vectors = []
        min_token_count = self.default_options.min_token_count or -np.inf
        for text in texts:
            tokens = self.encoder.encode(text)
            token_counts = Counter(tokens)
            non_zero_dims = []
            non_zero_vals = []

            for token, count in token_counts.items():
                if count < min_token_count:
                    continue
                non_zero_dims.append(token)
                non_zero_vals.append(count)

            vectors.append(SparseVector(non_zero_dims, non_zero_vals, self.dim))
        return vectors
