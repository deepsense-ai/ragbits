"""
Ragbits Document Search Example: DocumentSearch from Config

This example demonstrates how to use the `DocumentSearch` class to search for documents with a more advanced setup.
We will use the `LiteLLMEmbeddings` class to embed the documents and the query, the `ChromaVectorStore` class to store
the embeddings, and the `LiteLLMReranker` class to rerank the search results. We will also use the `LLMQueryRephraser`
class to rephrase the query.

The script performs the following steps:

        1. Create a list of documents.
        2. Initialize the `DocumentSearch` class with the predefined configuration.
        3. Ingest the documents into the `DocumentSearch` instance.
        4. Search for documents using a query.
        5. Print the search results.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/from_config.py
    ```
"""
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[chroma]",
# ]
# ///

import asyncio

from ragbits.core import audit
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

audit.set_trace_handlers("cli")

documents = [
    DocumentMeta.create_text_document_from_literal(
        """
        RIP boiled water. You will be mist.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why doesn't James Bond fart in bed? Because it would blow his cover.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why programmers don't like to swim? Because they're scared of the floating points.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        This one is completely unrelated.
        """
    ),
]

config = {
    "embedder": {
        "type": "ragbits.core.embeddings.litellm:LiteLLMEmbeddings",
    },
    "vector_store": {
        "type": "ragbits.core.vector_stores.chroma:ChromaVectorStore",
        "config": {
            "client": {
                "type": "PersistentClient",
                "config": {
                    "path": "chroma",
                },
            },
            "index_name": "jokes",
            "distance_method": "l2",
            "default_options": {
                "k": 3,
                "max_distance": 1.2,
            },
            "metadata_store": {
                "type": "InMemoryMetadataStore",
            },
        },
    },
    "reranker": {
        "type": "ragbits.document_search.retrieval.rerankers.litellm:LiteLLMReranker",
        "config": {
            "model": "cohere/rerank-english-v3.0",
            "default_options": {
                "top_n": 3,
                "max_chunks_per_doc": None,
            },
        },
    },
    "providers": {"txt": {"type": "DummyProvider"}},
    "rephraser": {
        "type": "LLMQueryRephraser",
        "config": {
            "llm": {
                "type": "ragbits.core.llms.litellm:LiteLLM",
                "config": {
                    "model_name": "gpt-4-turbo",
                },
            },
            "prompt": "QueryRephraserPrompt",
        },
    },
}


async def main() -> None:
    """
    Run the example.
    """
    document_search = DocumentSearch.from_config(config)

    await document_search.ingest(documents)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
