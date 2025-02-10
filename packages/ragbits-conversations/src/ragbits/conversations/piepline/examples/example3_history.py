import asyncio

from rich import print as pprint

from ragbits.conversations.piepline.pipeline import ConversationPiepline
from ragbits.conversations.piepline.plugins import AddHistoryPlugin, DocumentSearchRAGPlugin
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search._main import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta


async def _ingest_documents() -> DocumentSearch:
    documents = [
        DocumentMeta.create_text_document_from_literal(
            """
            The user's favorite fruit is pinaple.
            """
        ),
        DocumentMeta.create_text_document_from_literal(
            """
            The user's favorite dessert is ice cream.
            """
        ),
    ]

    embedder = LiteLLMEmbeddings(
        model="text-embedding-3-small",
    )
    vector_store = InMemoryVectorStore()
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )

    await document_search.ingest(documents)
    return document_search


history = [
    {"role": "user", "content": "Remember that whenever I talk about 'fruit', I mean 'dessert'. It's our secret code."},
    {"role": "assistant", "content": "I understand. I will now interpret 'fruit' as 'dessert'."},
]


async def main() -> None:
    """
    Example of using convcrsation pipeline
    """
    llm = LiteLLM("gpt-4o")
    document_search = await _ingest_documents()

    pipeline = ConversationPiepline(
        llm,
        plugins=[
            DocumentSearchRAGPlugin(document_search),
            AddHistoryPlugin(history),
        ],
    )
    question = "What is my favorite fruit?"
    result = await pipeline.run(question)
    pprint("[b][blue]The user asked:[/blue][b]")
    pprint(question)
    print()

    pprint("[b][blue]The LLM generated the following response:[/blue][b]\n")
    async for response in result.output_stream:
        pprint(response, end="", flush=True)

    pprint("\n\n[b][blue]The plugin metadata is:[/blue][b]\n")
    pprint(result.plugin_metadata)


if __name__ == "__main__":
    asyncio.run(main())
