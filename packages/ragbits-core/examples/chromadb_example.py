# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[litellm]",
# ]
# ///
import asyncio

import chromadb

from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_store.chromadb_store import ChromaDBStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

documents = [
    DocumentMeta.create_text_document_from_literal("RIP boiled water. You will be mist."),
    DocumentMeta.create_text_document_from_literal(
        "Why programmers don't like to swim? Because they're scared of the floating points."
    ),
]


async def main():
    """Run the example."""

    chroma_client = chromadb.PersistentClient(path="chroma")
    embedding_client = LiteLLMEmbeddings()

    vector_store = ChromaDBStore(
        index_name="jokes",
        chroma_client=chroma_client,
        embedding_function=embedding_client,
    )
    document_search = DocumentSearch(embedder=vector_store.embedding_function, vector_store=vector_store)

    for document in documents:
        await document_search.ingest_document(document)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
