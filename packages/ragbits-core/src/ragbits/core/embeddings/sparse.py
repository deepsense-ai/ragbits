from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

import tiktoken

from ragbits.core.utils.config_handling import WithConstructionConfig


@dataclass
class SparseVector:
    """Sparse Vector representation"""

    non_zero_dims: list[int]
    non_zero_vals: list[int]
    dim: int

    def __post_init__(self) -> None:
        if len(self.non_zero_dims) != len(self.non_zero_vals):
            raise ValueError("It should be same number of non zero values and non zero positions")
        if any(dim >= self.dim or dim < 0 for dim in self.non_zero_dims):
            raise ValueError("Indexes should be in the range of the vector dim")

    def __repr__(self) -> str:
        return f"SparseVector(non_zero_dims={self.non_zero_dims}, non_zero_vals={self.non_zero_vals}, dim={self.dim})"


class SparseEmbedding(WithConstructionConfig, ABC):
    """Sparse embedding interface"""

    @abstractmethod
    def embed_text(self, texts: list[str]) -> list[SparseVector]:
        """Transforms a list of texts into sparse vectors"""


class BagofTokens(SparseEmbedding):
    """BagofTokens implementations of sparse Embeddings interface"""

    def __init__(self, encoding_name: str):
        """
        Initializes the BagOfTokens embedding
        Args:
            encoding_name: Name of encoding to be used. Needs to be supported by tiktoken library.
        """
        self.encoder = tiktoken.get_encoding(encoding_name=encoding_name)
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
        for text in texts:
            tokens = self.encoder.encode(text)
            token_counts = Counter(tokens)
            non_zero_dims = []
            non_zero_vals = []

            for token, count in token_counts.items():
                non_zero_dims.append(token)
                non_zero_vals.append(count)

            vectors.append(SparseVector(non_zero_dims, non_zero_vals, self.dim))
        return vectors
