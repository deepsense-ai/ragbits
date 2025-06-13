# Tutorial: Retrieval-Augmented Generation (RAG)

Let's now go through a more advanced **question answering system** with **retrieval-augmented generation** (RAG) in Ragbits. We will use the same dataset as in [the previous tutorial](./intro.md), but we will try to improve the performance.

Install the latest Ragbits via `pip install -U ragbits[qdrant]` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4.1-nano` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Setting up the retriever

First, let's download the corpus data that we will use for RAG search. To make this fast and cheap to run, we have downsampled the original corpus to 28,000 documents.

Before we can search through our documents, we need to parse them into a format that Ragbits can understand. Since our data comes in JSONL format (JSON Lines), we will create a custom document parser that can handle this specific format.

```python
import json

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.ingestion.parsers import DocumentParser

# truncate long docs
MAX_CHARACTERS = 6000

class RAGQADocumentParser(DocumentParser):
    supported_document_types = {DocumentType.JSONL}

    async def parse(self, document: Document) -> list[Element]:
        return [
            TextElement(
                content=parsed["text"][:MAX_CHARACTERS],
                document_meta=document.metadata,
            )
            for line in document.local_path.read_text().strip().split("\n")
            if (parsed := json.loads(line))
        ]
```

Now we will configure our document search pipeline using Qdrant as the vector database and OpenAI's embeddings for semantic search. We will also ingest the data into our vector store.

```python hl_lines="17"
from qdrant_client import AsyncQdrantClient
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.vector_stores import VectorStoreOptions
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.ingestion.parsers import DocumentParserRouter
from ragbits.document_search.ingestion.strategies import BatchedIngestStrategy

retriever = DocumentSearch(
    vector_store=QdrantVectorStore(
        client=AsyncQdrantClient(path="./ragqa_arena_tech_corpus"),
        embedder=LiteLLMEmbedder(model_name="text-embedding-3-small"),
        default_options=VectorStoreOptions(k=5),
        index_name="ragqa_arena_tech_corpus",
    ),
    ingest_strategy=BatchedIngestStrategy(index_batch_size=1000),
    parser_router=DocumentParserRouter({DocumentType.JSONL: RAGQADocumentParser()}),
)
```

```python
import asyncio

async def main() -> None:
    results = await retriever.ingest("web://https://huggingface.co/datasets/deepsense-ai/ragbits/resolve/main/ragqa_arena_tech_corpus.jsonl")
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
IngestExecutionResult(
    successful=[
        IngestDocumentResult(
            document_uri='web://https://huggingface.co/datasets/deepsense-ai/ragbits/resolve/main/ragqa_arena_tech_corpus.jsonl',
            num_elements=28436,
            error=None
        )
    ],
    failed=[]
)
```

## Building RAG pipeline

In the previous tutorial, we looked at the low-level Ragbits components in isolation like [`Prompt`][ragbits.core.prompt.Prompt] or [`LLM`][ragbits.core.llms.base.LLM].

What if we want to build a pipeline that has multiple steps? For RAG, we need to combine retrieval and generation seamlessly. Let's start by creating prompts that can handle both questions and retrieved context.

First, we'll create prompts that can work with retrieved context. Notice how we modify our input model to accept both a question and optional context from our retriever.

```python
from collections.abc import Sequence

from pydantic import BaseModel
from ragbits.core.prompt import Prompt
from ragbits.document_search.documents.element import Element

class QuestionAnswerPromptInput(BaseModel):
    question: str
    context: Sequence[Element] | None = None

class CoTQuestionAnswerPromptOutput(BaseModel):
    reason: str
    answer: str

class CoTQuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, CoTQuestionAnswerPromptOutput]):
    system_prompt = """
    You are a question answering agent. Answer the question that will be provided using context.
    If in the given context there is not enough information refuse to answer.
    Think step by step.
    """
    user_prompt = """
    Question: {{ question }}
    Context: {% for chunk in context %}{{ chunk.text_representation }}{%- endfor %}
    """
```

The syntax below with [`Agent`][ragbits.agents.Agent] allows you to connect a few pieces together, in this case, our retriever and a generation component, so the whole system can be evaluated and optimized.

The [`Agent`][ragbits.agents.Agent] class allows you to connect retrieval and generation components together, creating a pipeline that can be evaluated and optimized as a whole. Here's how we create a RAG agent that inherits from `QuestionAnswerAgent` that we used in the previous tutorial.

```python hl_lines="5 7"
from ragbits.agents import AgentOptions, AgentResult
from ragbits.agents.types import QuestionAnswerAgent

class QuestionAnswerAgentWithRAG(QuestionAnswerAgent):
    async def run(self, input: QuestionAnswerPromptInput, options: AgentOptions | None = None) -> AgentResult[CoTQuestionAnswerPromptOutput]:
        context = await retriever.search(input.question)
        return await super().run(QuestionAnswerPromptInput(question=input.question, context=context))
```

Now let's put it all together and test our RAG pipeline.

```python hl_lines="4"
from ragbits.core.llms import LiteLLM

llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)
rag = QuestionAnswerAgentWithRAG(llm=llm, prompt=CoTQuestionAnswerPrompt)
```

```python hl_lines="2-4"
async def main() -> None:
    response = await rag.run(QuestionAnswerPromptInput(
        question="What are high memory and low memory on linux?",
    ))
    print(response.content.answer)

if __name__ == "__main__":
    asyncio.run(main())
```

```text
In Linux, high memory (HighMem) refers to a segment of physical memory that is not permanently mapped
in the kernel's address space, requiring temporary mapping when accessed. Low memory (LowMem) is memory
that is always mapped and directly accessible by the kernel. High memory is typically used for user-space
programs or caches, and accessing it involves special handling like calling kmap.
```

## Evaluating the system

In [the previous tutorial](./intro.md) with a simple CoT prompt, we got around 68% in terms of answer correctness on our devset. Would this RAG pipeline score better?

```python hl_lines="26"
from ragbits.core.sources import WebSource
from ragbits.evaluate.dataloaders.question_answer import QuestionAnswerDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics import MetricSet
from ragbits.evaluate.metrics.question_answer import QuestionAnswerAnswerCorrectness
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerPipeline

async def main() -> None:
    # Define the data loader
    source = WebSource(url="https://huggingface.co/datasets/deepsense-ai/ragbits/resolve/main/ragqa_arena_tech_examples.jsonl")
    dataloader=QuestionAnswerDataLoader(
        source=source,
        split="data[:100]",
        question_key="question",
        answer_key="response",
    )

    # Define the metric
    judge = LiteLLM(model_name="gpt-4.1")
    metric = QuestionAnswerAnswerCorrectness(judge)

    # Run the evaluation
    evaluator = Evaluator()
    results = await evaluator.compute(
        dataloader=dataloader,
        pipeline=QuestionAnswerPipeline(rag),
        metricset=MetricSet(metric),
    )
    print(results.metrics)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
{'LLM_based_answer_correctness': 0.81625} # Your result may differ
```

## Conclusions

Improving from around 68% to approximately 81% on this task, in terms of answer correctness, was pretty easy. But Ragbits gives you paths to continue iterating on the quality of your system and we have barely scratched the surface.

In general, you have the following tools:

- **Query Rephrasing**: Automatically rephrase user questions into multiple variations to capture different semantic angles and improve retrieval recall, especially for ambiguous or poorly-worded queries.
- **Hybrid Vector Search**: Combine dense vector embeddings with sparse keyword-based search (like BM25) to leverage both semantic similarity and exact keyword matching for more comprehensive document retrieval.
- **Reranking**: Apply a secondary ranking model to reorder retrieved documents based on their relevance to the specific query, filtering out less relevant results before they reach the language model.

Check the [Document Search guide](../how-to/document_search/search-documents.md) to learn more about available retrieval techniques.
