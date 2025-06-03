---
hide:
  - navigation
---

# Ragbits docs

<style>
.md-content .md-typeset #ragbits-docs { display: none; }

#main-header {
    font-size: 3em;
    margin-bottom: 0;
}
</style>

<h1 align="center" id="main-header">🐰 Ragbits</h1>

<p align="center">
  <em size="">Building blocks for rapid development of GenAI applications.</em>
</p>

<div align="center">

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - License" src="https://img.shields.io/pypi/l/ragbits">
</a>

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/ragbits">
</a>

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/ragbits">
</a>

</div>
---

## Features

### 🔨 Build Reliable & Scalable GenAI Apps

- **Swap LLMs anytime** – Switch between [100+ LLMs via LiteLLM](https://ragbits.deepsense.ai/how-to/llms/use_llms/) or run [local models](https://ragbits.deepsense.ai/how-to/llms/use_local_llms/)).
- **Type-safe LLM calls** – Use Python generics to [enforce strict type safety](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/#how-to-configure-prompts-output-data-type) in model interactions.
- **Bring your own vector store** – Connect to [Qdrant](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), [PgVector](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.pgvector.PgVectorStore), and more with built-in support.
- **Developer tools included** – [Manage vector stores](https://ragbits.deepsense.ai/cli/main/#ragbits-vector-store), query pipelines, and [test prompts from your terminal](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/#testing-the-prompt-from-the-cli).
- **Modular installation** – Install only what you need, reducing dependencies and improving performance.

### 📚 Fast & Flexible RAG Processing

- **Ingest 20+ formats** – Process PDFs, HTML, spreadsheets, presentations, and more. Process data using [unstructured](https://unstructured.io/) or create a custom provider.
- **Handle complex data** – Extract tables, images, and structured content with built-in VLMs support.
- **Connect to any data source** – Use prebuilt connectors for S3, GCS, Azure, or implement your own.
- **Scale ingestion** – Process large datasets quickly with [Ray-based parallel processing](https://ragbits.deepsense.ai/how-to/document_search/distributed_ingestion/#how-to-ingest-documents-in-a-distributed-fashion).

### 🚀 Deploy & Monitor with Confidence

- **Real-time observability** – Track performance with [OpenTelemetry](https://ragbits.deepsense.ai/how-to/project/use_tracing/#opentelemetry-trace-handler) and [CLI insights](https://ragbits.deepsense.ai/how-to/project/use_tracing/#cli-trace-handler).
- **Built-in testing** – Validate prompts [with promptfoo](https://ragbits.deepsense.ai/how-to/prompts/promptfoo/) before deployment.
- **Auto-optimization** – Continuously evaluate and refine model performance.
- **Visual testing UI (Coming Soon)** – Test and optimize applications with a visual interface.

## Installation

To get started quickly, you can install with:

=== "pip"

    ```sh
    pip install ragbits
    ```

=== "uv"

    ```sh
    uv add ragbits
    ```

This is a starter bundle of packages, containing:

- [`ragbits-core`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-core) - fundamental tools for working with prompts, LLMs and vector databases.
- [`ragbits-agents`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-agents) - abstractions for building agentic systems.
- [`ragbits-document-search`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-document-search) - retrieval and ingestion piplines for knowledge bases.
- [`ragbits-evaluate`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-evaluate) - unified evaluation framework for Ragbits components.
- [`ragbits-chat`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-chat) - full-stack infrastructure for building conversational AI applications.
- [`ragbits-cli`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-cli) - `ragbits` shell command for interacting with Ragbits components.

Alternatively, you can use individual components of the stack by installing their respective packages.

## Quickstart

### Large Language Models

To define prompts and run LLMs:

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

class QuestionAnswerPromptInput(BaseModel):
    question: str

class QuestionAnswerPromptOutput(BaseModel):
    answer: str

class QuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, QuestionAnswerPromptOutput]):
    system_prompt = """
    You are a question answering agent. Answer the question to the best of your ability.
    """
    user_prompt = """
    Question: {{ question }}
    """

llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)

async def main() -> None:
    prompt = QuestionAnswerPrompt(QuestionAnswerPromptInput(question="What are high memory and low memory on linux?"))
    response = await llm.generate(prompt)
    print(response.answer)

if __name__ == "__main__":
    asyncio.run(main())
```

### Document Search

To build and query a simple vector store index using OpenAI:

```python
import asyncio
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
vector_store = InMemoryVectorStore(embedder=embedder)
document_search = DocumentSearch(vector_store=vector_store)

async def run() -> None:
    await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")
    result = await document_search.search("What are the key findings presented in this paper?")
    print(result)

if __name__ == "__main__":
    asyncio.run(run())
```

### Retrieval-Augmented Generation

To build a simple RAG pipeline:

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

class QuestionAnswerPromptInput(BaseModel):
    question: str
    context: list[str]

class QuestionAnswerPromptOutput(BaseModel):
    answer: str

class QuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, QuestionAnswerPromptOutput]):
    system_prompt = """
    You are a question answering agent. Answer the question that will be provided using context.
    If in the given context there is not enough information refuse to answer.
    """
    user_prompt = """
    Question: {{ question }}
    Context: {% for item in context %}{{ item }}{%- endfor %}
    """

embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
vector_store = InMemoryVectorStore(embedder=embedder)
document_search = DocumentSearch(vector_store=vector_store)
llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)

async def run() -> None:
    question = "What are the key findings presented in this paper?"

    await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")
    result = await document_search.search(question)

    prompt = QuestionAnswerPrompt(QuestionAnswerPromptInput(
        question=question,
        context=[element.text_representation for element in result],
    ))
    response = await llm.generate(prompt)
    print(response.answer)

if __name__ == "__main__":
    asyncio.run(run())
```

## Rapid development

Create Ragbits projects from templates:

```sh
uvx create-ragbits-app
```

Explore `create-ragbits-app` repo [here](https://github.com/deepsense-ai/create-ragbits-app). If you have a new idea for a template, feel free to contribute!

## Documentation

- [Quickstart](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/) - Get started with Ragbits in a few minutes
- [How-to](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/) - Learn how to use Ragbits in your projects
- [CLI](https://ragbits.deepsense.ai/cli/main/) - Learn how to run Ragbits in your terminal
- [API reference](https://ragbits.deepsense.ai/api_reference/core/prompt/) - Explore the underlying Ragbits API
