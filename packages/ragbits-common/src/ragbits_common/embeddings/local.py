from typing import Any, Iterator, Optional

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    HAS_LOCAL_EMBEDDINGS = True
except ImportError:
    HAS_LOCAL_EMBEDDINGS = False

from ragbits_common.embeddings.base import Embeddings


def _batch(iterable: Any, per_batch: int = 1) -> Iterator:
    length = len(iterable)
    for ndx in range(0, length, per_batch):
        yield iterable[ndx : min(ndx + per_batch, length)]


def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


class LocalEmbeddings(Embeddings):
    """
    Class for interaction with any encoder available in HuggingFace.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use.
            api_key: The API key for Hugging Face authentication.
        """
        if not HAS_LOCAL_EMBEDDINGS:
            raise ImportError("You need to install the 'local' extra requirements to use local embeddings models")

        super().__init__()

        self.hf_api_key = api_key
        self.model_name = model_name

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModel.from_pretrained(self.model_name, token=self.hf_api_key).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.hf_api_key)

    async def embed_text(self, data: list[str], batch_size: int = 1) -> list[list[float]]:
        """
        Calls the appropriate encoder endpoint with the given data and options.

        Args:
            data: List of strings to get embeddings for.
            batch_size: Batch size.

        Returns:
            List of embeddings for the given strings.
        """

        embeddings = []
        for batch in _batch(data, batch_size):
            batch_dict = self.tokenizer(
                batch, max_length=self.tokenizer.model_max_length, padding=True, truncation=True, return_tensors="pt"
            ).to(self.device)
            with torch.no_grad():
                outputs = self.model(**batch_dict)
                batch_embeddings = _average_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
                batch_embeddings = F.normalize(batch_embeddings, p=2, dim=1)
            embeddings.extend(batch_embeddings.to("cpu").tolist())

        torch.cuda.empty_cache()
        return embeddings
