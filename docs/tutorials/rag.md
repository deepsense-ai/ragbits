# Tutorial: Retrieval-Augmented Generation (RAG)

Let's now go through a more advanced **question answering system** with **retrieval-augmented generation** (RAG) in Ragbits. We will use the same dataset as in [the previous tutorial](./intro.md), but we will try to improve the performance.

Install the latest Ragbits via `pip install -U ragbits[qdrant]` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4.1-nano` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Setting up the retriever

First, let's download the corpus data that we will use for RAG search. To make this fast and cheap to run, we've downsampled the original corpus to 28,000 documents.
As far as Ragbits is concerned, you can plug in any Python code for calling tools or retrievers. Here, we'll just use OpenAI Embeddings and do top-K search locally, just for convenience.

```python
import json

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.ingestion.parsers import DocumentParser

# for truncating >99th percentile of documents
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

```python
import asyncio

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

async def main() -> None:
    results = await retriever.ingest("web://https://huggingface.co/dspy/cache/resolve/main/ragqa_arena_tech_corpus.jsonl")
    print(results)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
IngestExecutionResult(
    successful=[
        IngestDocumentResult(
            document_uri='web:https://huggingface.co/dspy/cache/resolve/main/ragqa_arena_tech_corpus.jsonl',
            num_elements=28436,
            error=None
        )
    ],
    failed=[]
)
```

## Building RAG pipeline

In the previous tutorial, we looked at the low-level Ragbits componenets in isolation e.g. [`Prompt`][ragbits.core.prompt.Prompt].

What if we want to build a pipeline that has multiple steps? The syntax below with [`Agent`][ragbits.agents.Agent] allows you to connect a few pieces together, in this case, our retriever and a generation component, so the whole system can be evaluated and optimized.

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

class QuestionAnswerPromptInput(BaseModel):
    question: str
    context: list | None = None

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
    Context: {% for item in context %}{{ item }}{%- endfor %}
    """
```

Set up responder:

```python
from ragbits.agents.types import QuestionAnswerAgent
from ragbits.core.llms import LiteLLM

llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)
responder = QuestionAnswerAgent(llm=llm, prompt=CoTQuestionAnswerPrompt)
```

Define a RAG pipeline:

```python
class QuestionAnswerAgentWithRAG(QuestionAnswerAgent):
    def __init__(self, responder: QuestionAnswerAgent, retriever: DocumentSearch) -> None:
        self.retriever = retriever
        self.responder = responder

    async def run(self, input: QuestionAnswerPromptInput, options: AgentOptions | None = None) -> AgentResult[QuestionAnswerPromptOutput]:
        context = await self.retriever.search(input.question)
        return await self.responder.run(QuestionAnswerPromptInput(question=input.question, context=context))
```

Let's use the RAG pipeline.

```python
rag = QuestionAnswerAgentWithRAG(responder=responder, retriever=retriever)

async def main() -> None:
    response = await rag.run(QuestionAnswerPromptInput(
        question="What are high memory and low memory on linux?",
    ))
    print(response.content.answer)

if __name__ == "__main__":
    asyncio.run(main())
```

```text
In Linux, high memory (HighMem) refers to a segment of physical memory that is not permanently mapped in the kernel's address space, requiring temporary mapping when accessed. Low memory (LowMem) is memory that is always mapped and directly accessible by the kernel. High memory is typically used for user-space programs or caches, and accessing it involves special handling like calling kmap.
```

## Evaluating the system

Earlier with a simple CoT prompt, we got around 68% in terms of answer correctness on our devset. Would this RAG pipeline score better?

```python
from ragbits.core.sources import WebSource
from ragbits.evaluate.dataloaders.question_answer import QuestionAnswerDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics import MetricSet
from ragbits.evaluate.metrics.question_answer import QuestionAnswerAnswerCorrectness
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerPipeline

async def main() -> None:
    # Define data loader
    source = WebSource(url="https://huggingface.co/dspy/cache/resolve/main/ragqa_arena_tech_examples.jsonl")
    dataloader=QuestionAnswerDataLoader(
        source=source,
        split="data[:100]",
        question_key="question",
        answer_key="response",
    )

    # Define metric
    judge = LiteLLM(model_name="gpt-4.1")
    metric = QuestionAnswerAnswerCorrectness(judge)

    # Run evaluation
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
{'LLM_based_answer_correctness': 0.76}
```

## Conclusions

...
