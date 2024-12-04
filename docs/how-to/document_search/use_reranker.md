# How-To: Use Reranker
`ragbits-document-search` contains a `Reranker` module that could be used to select the most relevant and high-quality information from a set of retrieved documents.

This guide will show you how to use `LiteLLMReranker` and how to create your custom implementation.


## LLM Reranker
`LiteLLMReranker` is based on [litellm.rerank()](https://docs.litellm.ai/docs/rerank) that supports three providers: Cohere, Azure AI, Together AI.
You will need to set a proper API key to use the reranking functionality.

To use a `LiteLLMReranker` within retrival pipeline you simply need to provide it as an argument to `DocumentSearch`.
```python
import os
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker

os.environ["COHERE_API_KEY"] = "<api_key>"

document_search = DocumentSearch(
    reranker=LiteLLMReranker("cohere/rerank-english-v3.0"),
    ...
)
```

The next example will show on how to use the basic usage of the same re-ranker as independent component:

```python
import asyncio
import os
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.documents.document import DocumentMeta

os.environ["COHERE_API_KEY"] = "<api_key>"


def create_text_element(text: str) -> TextElement:
    document_meta = DocumentMeta.create_text_document_from_literal(content=text)
    text_element = TextElement(document_meta=document_meta, content=text)
    return text_element


async def main():
    reranker = LiteLLMReranker(model="cohere/rerank-english-v3.0")
    text_elements = [
        create_text_element(
            text="The artificial inteligence development is a milestone for global information accesibility"
        ),
        create_text_element(text="The redpill will show you the true nature of things"),
        create_text_element(text="The bluepill will make you stay in the state of ignorance"),
    ]
    query = "Take the pill and follow the rabbit!"
    ranked = await reranker.rerank(elements=text_elements, query=query)
    for element in ranked:
        print(element.content + "\n")


asyncio.run(main())
```

The console should print the contents of the ranked elements in order of their relevance to the query, as determined by the model.

```text
The redpill will show you the true nature of things

The bluepill will make you stay in the state of ignorance

The artificial inteligence development is a milestone for global information accesibility
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
```