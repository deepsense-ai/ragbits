from collections import Counter

import tiktoken

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import SparseVector, VectorSize
from ragbits.core.embeddings.sparse.base import SparseEmbedder
from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven


class BagOfTokensOptions(Options):
    """A dataclass with definition of BOT options"""

    model_name: str | None | NotGiven = "gpt-4o"
    encoding_name: str | None | NotGiven = NOT_GIVEN
    min_token_count: int | None | NotGiven = NOT_GIVEN


class BagOfTokens(SparseEmbedder[BagOfTokensOptions]):
    """BagOfTokens implementations of sparse Embedder interface"""

    options_cls = BagOfTokensOptions

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this BagOfTokens model.

        For BagOfTokens, this returns the tokenizer vocabulary size.

        Returns:
            VectorSize object with is_sparse=True and the vocabulary size.
        """
        merged_options = self.default_options

        if merged_options.encoding_name and merged_options.model_name:
            raise ValueError("Please specify only one of encoding_name or model_name")
        if not (merged_options.encoding_name or merged_options.model_name):
            raise ValueError("Either encoding_name or model_name needs to be specified")

        if merged_options.encoding_name:
            encoder = tiktoken.get_encoding(encoding_name=merged_options.encoding_name)
        elif merged_options.model_name:
            encoder = tiktoken.encoding_for_model(model_name=merged_options.model_name)
        else:
            raise ValueError("Either encoding_name or model_name needs to be specified")

        # Get the vocabulary size from the encoder
        vocab_size = encoder.n_vocab
        return VectorSize(size=vocab_size, is_sparse=True)

    async def embed_text(self, texts: list[str], options: BagOfTokensOptions | None = None) -> list[SparseVector]:
        """
        Transforms a list of texts into sparse vectors using bag-of-tokens representation.

        Args:
            texts: list of input texts.
            options: optional embedding options

        Returns:
            list of SparseVector instances.
        """
        vectors = []
        merged_options = self.default_options | options if options else self.default_options
        with trace(data=texts, options=merged_options.dict()) as outputs:
            if merged_options.encoding_name and merged_options.model_name:
                raise ValueError("Please specify only one of encoding_name or model_name")
            if not (merged_options.encoding_name or merged_options.model_name):
                raise ValueError("Either encoding_name or model_name needs to be specified")

            if merged_options.encoding_name:
                encoder = tiktoken.get_encoding(encoding_name=merged_options.encoding_name)
            elif merged_options.model_name:
                encoder = tiktoken.encoding_for_model(model_name=merged_options.model_name)
            else:
                raise ValueError("Either encoding_name or model_name needs to be specified")

            min_token_count = merged_options.min_token_count or float("-inf")
            for text in texts:
                tokens = encoder.encode(text)
                token_counts = Counter(tokens)
                non_zero_dims = []
                non_zero_vals = []

                for token, count in token_counts.items():
                    if count < min_token_count:
                        continue
                    non_zero_dims.append(token)
                    non_zero_vals.append(float(count))

                vectors.append(SparseVector(indices=non_zero_dims, values=non_zero_vals))
            outputs.embeddings = vectors
        return vectors
