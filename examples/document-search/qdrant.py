import asyncio

from qdrant_client import AsyncQdrantClient

from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
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
    embedder = LiteLLMEmbeddings(
        model="text-embedding-3-small",
    )
    vector_store = QdrantVectorStore(
        client=AsyncQdrantClient(path="./qdrant"),
        collection_name="jokes",
    )
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    all_documents = await vector_store.list()

    print()
    print("All documents:")
    print([doc.metadata["content"] for doc in all_documents])

    query = "I'm boiling my water and I need a joke"
    vector_store_kwargs = {
        "k": 2,
        "max_distance": None,
    }
    results = await document_search.search(
        query,
        config=SearchConfig(vector_store_kwargs=vector_store_kwargs),
    )

    print()
    print(f"Documents similar to: {query}")
    print([element.get_key() for element in results])


if __name__ == "__main__":
    asyncio.run(main())
