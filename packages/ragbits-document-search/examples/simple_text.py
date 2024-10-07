# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits[litellm]",
# ]
# ///
import asyncio

from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_store.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

documents = [
    DocumentMeta.create_text_document_from_literal("RIP boiled water. You will be mist."),
    DocumentMeta.create_text_document_from_literal(
        "Why doesn't James Bond fart in bed? Because it would blow his cover."
    ),
    DocumentMeta.create_text_document_from_literal(
        "Why programmers don't like to swim? Because they're scared of the floating points."
    ),
]


async def main():
    """Run the example."""

    document_search = DocumentSearch(embedder=LiteLLMEmbeddings(), vector_store=InMemoryVectorStore())

    for document in documents:
        await document_search.ingest_document(document)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
