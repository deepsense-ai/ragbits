# How-To: Use Reranker
`ragbits-document-search` contains a `Reranker` module that could be used to select the most relevant and high-quality information from a set of retrieved documents.

This guide will show you how to use `LiteLLMReranker` and how to create your custom implementation.


## LLM Reranker
`LiteLLMReranker` is based on [litellm.rerank()](https://docs.litellm.ai/docs/rerank) that supports three providers: Cohere, Azure AI, Together AI.
You will need to set a proper API key to use the reranking functionality.

To use a `LiteLLMReranker` you simply need to provide it as an argument to `DocumentSearch`.
```python
import os
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker

os.environ["COHERE_API_KEY"] = "<api_key>"

document_search = DocumentSearch(
    reranker=LiteLLMReranker("cohere/rerank-english-v3.0"),
    ...
)
```

## Custom Reranker
To create a custom Reranker you need to extend the `Reranker` class:
```python
from collections.abc import Sequence

from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions
from ragbits.document_search.documents.element import Element

class CustomReranker(Reranker):
    async def rerank(
        self,
        elements: Sequence[Element],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        pass

    @classmethod
    def from_config(cls, config: dict) -> "CustomReranker":
        pass
```