# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[litellm]",
# ]
# ///
import asyncio

import chromadb

from ragbits.core.embeddings import LiteLLMEmbeddings
from ragbits.core.vector_store.chromadb_store import ChromaDBStore
from ragbits.document_search import DocumentSearch, SearchConfig
from ragbits.document_search.documents.document import DocumentMeta

documents = [
    DocumentMeta.create_text_document_from_literal("RIP boiled water. You will be mist."),
    DocumentMeta.create_text_document_from_literal(
        "Why programmers don't like to swim? Because they're scared of the floating points."
    ),
    DocumentMeta.create_text_document_from_literal("This one is completely unrelated."),
]


async def main() -> None:
    """
    Run the example.
    """
    chroma_client = chromadb.PersistentClient(path="chroma")
    embedding_client = LiteLLMEmbeddings()

    vector_store = ChromaDBStore(
        index_name="jokes",
        chroma_client=chroma_client,
        embedding_function=embedding_client,
    )
    document_search = DocumentSearch(embedder=vector_store.embedding_function, vector_store=vector_store)

    await document_search.ingest(documents)

    print()
    print("All documents:")
    all_documents = await vector_store.list()
    print([doc.metadata["content"] for doc in all_documents])

    query = "I'm boiling my water and I need a joke"
    print()
    print(f"Documents similar to: {query}")
    results = await document_search.search(query, search_config=SearchConfig(vector_store_kwargs={"k": 2}))
    print([element.get_key() for element in results])


if __name__ == "__main__":
    asyncio.run(main())
