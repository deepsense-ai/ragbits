# Quickstart 2: Adding RAG Capabilities

In this chapter, we will explore how to use Ragbit's Document Search capabilities to retrieve relevant documents for your prompts. This technique is based on the Retrieval Augmented Generation (RAG) architecture, which allows the LLM to generate responses informed by relevant information from your documents.

To work with document content, we first need to "ingest" them (i.e., process, embed, and store them in a vector database). Afterwards, we can search for relevant documents based on the user's input and use the retrieved information to enhance the LLM's response.

We will continue with the example of generating custom songs. In the previous chapters, you learned how to define a prompt and interact with it using the `ragbits` CLI. We will now upgrade the prompt with a document search capability to provide the LLM with additional context when generating a song on the given subject (in this case: inspirations from children's stories).

## Getting the Documents

To leverage the RAG capabilities, you need to provide a set of documents that the model can use to generate responses. This guide uses an [open-licensed (CC-BY 4.0) collection of children's stories](https://github.com/global-asp/pb-source/tree/master) as examples. You should download these documents and place them next to your Python file:

```bash
git clone https://github.com/global-asp/pb-source.git
```

The short stories are in Markdown format. Ragbits supports [various document formats][ragbits.document_search.documents.document.DocumentType], including PDF and DOC, as well as non-textual files such as images.

## Defining the Document Search Object

The `DocumentSearch` class serves as the main entry point for working with documents in Ragbits. It requires an embedder and a vector store to work. This example uses the `LiteLLMEmbeddings` embedder and the `InMemoryVectorStore` vector store:

```python
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

embedder = LiteLLMEmbeddings(
    model="text-embedding-3-small",
)
vector_store = InMemoryVectorStore()
document_search = DocumentSearch(
    embedder=embedder,
    vector_store=vector_store,
)
```

!!! note
    `InMemoryVectorStore` is a simple in-memory vector store suitable for demonstration purposes. In real-world scenarios, you would typically use one of the persistent vector stores like [`ChromaVectorStore`][ragbits.core.vector_stores.chroma.ChromaVectorStore] or [`QdrantVectorStore`][ragbits.core.vector_stores.qdrant.QdrantVectorStore].

## Defining the Source of the Documents

We first need to direct Ragbits to the location of the documents to load them. This code will load the first 100 documents from the `pb-source/en` directory:

```python
from pathlib import Path
from ragbits.document_search.documents.sources.local import LocalFileSource

# Path to the directory with markdown files to ingest
documents_path = Path(__file__).parent / "pb-source/en"
documents = LocalFileSource.list_sources(documents_path, file_pattern="*.md")[:100]
```

Because the documents are stored locally, we are using `LocalFileSource` here. Ragbits also supports a variety of other sources including Google Cloud Storage, Hugging Face, and custom sources.

## Ingesting the Documents

Having established the documents and the `DocumentSearch` object, we can now ingest the documents:

```python
import asyncio

async def main():
    await document_search.ingest(documents)

if __name__ == "__main__":
    asyncio.run(main())
```

This procedure will process, embed, and store the documents in the vector database.

Now, we can use the `document_search` object to find relevant documents. Let’s try a manual search:

```python
print(await document_search.search("school"))
```

This function will return fragments of ingested documents that semantically match the query “school.”

## Using the Documents in the Prompt

To include the retrieved documents in the prompt, we need to modify the prompt defined in [Quickstart 1](quickstart1_prompts.md).

First, we'll alter the data model of the prompt to include the retrieved documents:

```python
from pydantic import BaseModel

class SongIdea(BaseModel):
    subject: str
    age_group: int
    genre: str
    inspirations: list[str]
```

The updated model looks similar to the earlier model, but now incorporates a new field, `inspirations`. This field will contain inspirations for the song, retrieved from the documents.

Next, we need to adjust the prompt to include these inspirations in the prompt text:

```python
from ragbits.core.prompt.prompt import Prompt

class SongPrompt(Prompt[SongIdea]):
    system_prompt = """
        You are a professional songwriter.
        {% if age_group < 18 %}
            You only use language that is appropriate for children.
        {% endif %}
    """

    user_prompt = """
        Write a song about a {{subject}} for {{age_group}} years old {{genre}} fans.

        Here are some fragments of short stories for inspiration:
        {% for inspiration in inspirations %}
            # Fragment {{loop.index}}
            {{inspiration}}

        {% endfor %}
    """
```

The prompt looks similar to the previous one but now includes a section with inspirations sourced from the retrieved documents.

## Using the Prompt with the LLM

Now that we have a prompt that includes inspirations from the documents, we can create a function that uses the LLM to generate a song given a subject, age group, and genre. At the same time, this function will automatically supply inspirations from the ingested documents:

```python
from ragbits.core.llms.litellm import LiteLLM

llm = LiteLLM("gpt-4")

async def get_song_idea(subject: str, age_group: int, genre: str) -> str:
    elements = await document_search.search(subject)
    inspirations = [element.text_representation for element in elements if element.text_representation]
    prompt = SongPrompt(SongIdea(subject=subject, age_group=age_group, genre=genre, inspirations=inspirations))

    return await llm.generate(prompt)
```

This function searches for documents related to the subject, extracts the text representations of the found elements, and passes them to the prompt alongside the subject, age group, and genre. The LLM then generates a song based on the provided prompt.

We can now modify the `main` function to use the function we just created:

```python
async def main():
    await document_search.ingest(documents)
    print(await get_song_idea("school", 10, "pop"))
```

!!! note
    In real-world scenarios, you wouldn’t simultaneously ingest and search for documents in the same function. You would ingest the documents once (or periodically) and then use the `document_search` object to search for relevant documents as needed.

## Conclusion

In this guide, you learned how to use Ragbits' Document Search capabilities to find documents relevant to the user's question and utilize them to enhance the LLM's responses. By incorporating the RAG architecture with your prompts, you can provide the LLM with additional context and information to produce more accurate and relevant responses.