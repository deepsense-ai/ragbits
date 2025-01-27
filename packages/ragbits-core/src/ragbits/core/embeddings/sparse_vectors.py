from abc import abstractmethod
from collections import Counter
from dataclasses import dataclass


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


class SparseEmbedding:
    """Sparse embedding interface"""

    @abstractmethod
    def embed_text(self, texts: list[str]) -> list[SparseVector]:
        """Transforms a list of texts into sparse vectors"""


class BagofTokens(SparseEmbedding):
    """BagofTokens implementations of sparse Embeddings interface"""

    def __init__(self, vocabulary: dict[str, int]):
        """
        Initializes the BagOfTokens embedding. If no vocabulary is provided, it will be built automatically.
        :param vocabulary: A mapping from token to its index in the embedding (optional).
        """
        self.vocabulary = vocabulary or {}
        self.dim = len(self.vocabulary)

    def _build_vocabulary(self, texts: list[str]) -> None:
        all_tokens = [token for text in texts for token in text.split()]  # also tokenizer?
        unique_tokens = list(set(all_tokens))
        self.vocabulary = {token: idx for idx, token in enumerate(unique_tokens)}
        self.dim = len(self.vocabulary)

    def embed(self, texts: list[str]) -> list[SparseVector]:
        """
        Transforms a list of texts into sparse vectors using bag-of-tokens representation.
        If the vocabulary is not defined, it will be built from the texts.
        :param texts: list of input texts.
        :return: list of SparseVector instances.
        """
        if not self.vocabulary:
            self._build_vocabulary(texts)

        vectors = []
        for text in texts:
            tokens = text.split()  # maybe here tokenizer usage?
            token_counts = Counter(tokens)

            non_zero_dims = []
            non_zero_vals = []

            for token, count in token_counts.items():
                non_zero_dims.append(self.vocabulary[token])
                non_zero_vals.append(count)

            vectors.append(SparseVector(non_zero_dims, non_zero_vals, self.dim))
        return vectors
