<div align="center">

<h1>🐰 Ragbits</h1>

*Building blocks for rapid development of GenAI applications*

[Homepage](https://deepsense.ai/rd-hub/ragbits/) | [Documentation](https://ragbits.deepsense.ai) | [Contact](https://deepsense.ai/contact/)

<a href="https://trendshift.io/repositories/13966" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13966" alt="deepsense-ai%2Fragbits | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>


[![PyPI - License](https://img.shields.io/pypi/l/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Version](https://img.shields.io/pypi/v/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ragbits)](https://pypi.org/project/ragbits)

</div>

---

## Features

### 🔨 Build Reliable & Scalable GenAI Apps

- **Swap LLMs anytime** – Switch between [100+ LLMs via LiteLLM](https://ragbits.deepsense.ai/stable/how-to/llms/use_llms/) or run [local models](https://ragbits.deepsense.ai/stable/how-to/llms/use_local_llms/).
- **Type-safe LLM calls** – Use Python generics to [enforce strict type safety](https://ragbits.deepsense.ai/stable/how-to/prompts/use_prompting/#how-to-configure-prompts-output-data-type) in model interactions.
- **Bring your own vector store** – Connect to [Qdrant](https://ragbits.deepsense.ai/stable/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), [PgVector](https://ragbits.deepsense.ai/stable/api_reference/core/vector-stores/#ragbits.core.vector_stores.pgvector.PgVectorStore), and more with built-in support.
- **Developer tools included** – [Manage vector stores](https://ragbits.deepsense.ai/stable/cli/main/#ragbits-vector-store), query pipelines, and [test prompts from your terminal](https://ragbits.deepsense.ai/stable/quickstart/quickstart1_prompts/#testing-the-prompt-from-the-cli).
- **Modular installation** – Install only what you need, reducing dependencies and improving performance.

### 📚 Fast & Flexible RAG Processing

- **Ingest 20+ formats** – Process PDFs, HTML, spreadsheets, presentations, and more. Process data using [Docling](https://github.com/docling-project/docling), [Unstructured](https://github.com/Unstructured-IO/unstructured) or create a custom parser.
- **Handle complex data** – Extract tables, images, and structured content with built-in VLMs support.
- **Connect to any data source** – Use prebuilt connectors for S3, GCS, Azure, or implement your own.
- **Scale ingestion** – Process large datasets quickly with [Ray-based parallel processing](https://ragbits.deepsense.ai/stable/how-to/document_search/distributed_ingestion/#how-to-ingest-documents-in-a-distributed-fashion).

### 🤖 Build Multi-Agent Workflows with Ease

- **Multi-agent coordination** – Create teams of specialized agents with role-based collaboration using [A2A protocol](https://ragbits.deepsense.ai/stable/tutorials/agents) for interoperability.
- **Real-time data integration** – Leverage [Model Context Protocol (MCP)](https://ragbits.deepsense.ai/stable/how-to/agents/provide_mcp_tools) for live web access, database queries, and API integrations.
- **Conversation state management** – Maintain context across interactions with [automatic history tracking](https://ragbits.deepsense.ai/stable/how-to/agents/define_and_use_agents/#conversation-history).

### 🚀 Deploy & Monitor with Confidence

- **Real-time observability** – Track performance with [OpenTelemetry](https://ragbits.deepsense.ai/stable/how-to/project/use_tracing/#opentelemetry-trace-handler) and [CLI insights](https://ragbits.deepsense.ai/stable/how-to/project/use_tracing/#cli-trace-handler).
- **Built-in testing** – Validate prompts [with promptfoo](https://ragbits.deepsense.ai/stable/how-to/prompts/promptfoo/) before deployment.
- **Auto-optimization** – Continuously evaluate and refine model performance.
- **Chat UI** – Deploy [chatbot interface](https://ragbits.deepsense.ai/stable/how-to/chatbots/api/) with API, persistance and user feedback.

## Installation

### Stable Release

To get started quickly, you can install the latest stable release with:

```sh
pip install ragbits
```

### Nightly Builds

For the latest development features, you can install nightly builds that are automatically published from the `develop` branch:

```sh
pip install ragbits --pre
```

**Note:** Nightly builds include the latest features and bug fixes but may be less stable than official releases. They follow the version format `X.Y.Z.devYYYYMMDDHHMM`.

### Package Contents

This is a starter bundle of packages, containing:

- [`ragbits-core`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-core) - fundamental tools for working with prompts, LLMs and vector databases.
- [`ragbits-agents`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-agents) - abstractions for building agentic systems.
- [`ragbits-document-search`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-document-search) - retrieval and ingestion piplines for knowledge bases.
- [`ragbits-evaluate`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-evaluate) - unified evaluation framework for Ragbits components.
- [`ragbits-guardrails`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-guardrails) - utilities for ensuring the safety and relevance of responses.
- [`ragbits-chat`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-chat) - full-stack infrastructure for building conversational AI applications.
- [`ragbits-cli`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-cli) - `ragbits` shell command for interacting with Ragbits components.

Alternatively, you can use individual components of the stack by installing their respective packages.

## Quickstart

### Basics

To define a prompt and run LLM:

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

class QuestionAnswerPromptInput(BaseModel):
    question: str

class QuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, str]):
    system_prompt = """
    You are a question answering agent. Answer the question to the best of your ability.
    """
    user_prompt = """
    Question: {{ question }}
    """

llm = LiteLLM(model_name="gpt-4.1-nano")

async def main() -> None:
    prompt = QuestionAnswerPrompt(QuestionAnswerPromptInput(question="What are high memory and low memory on linux?"))
    response = await llm.generate(prompt)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Document Search

To build and query a simple vector store index:

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
from collections.abc import Iterable
from pydantic import BaseModel
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.element import Element

class QuestionAnswerPromptInput(BaseModel):
    question: str
    context: Iterable[Element]

class QuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, str]):
    system_prompt = """
    You are a question answering agent. Answer the question that will be provided using context.
    If in the given context there is not enough information refuse to answer.
    """
    user_prompt = """
    Question: {{ question }}
    Context: {% for chunk in context %}{{ chunk.text_representation }}{%- endfor %}
    """

llm = LiteLLM(model_name="gpt-4.1-nano")
embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
vector_store = InMemoryVectorStore(embedder=embedder)
document_search = DocumentSearch(vector_store=vector_store)

async def run() -> None:
    question = "What are the key findings presented in this paper?"

    await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")
    chunks = await document_search.search(question)

    prompt = QuestionAnswerPrompt(QuestionAnswerPromptInput(question=question, context=chunks))
    response = await llm.generate(prompt)
    print(response)

if __name__ == "__main__":
    asyncio.run(run())
```

### Agentic RAG

To build an agentic RAG pipeline:

```python
import asyncio
from ragbits.agents import Agent
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
vector_store = InMemoryVectorStore(embedder=embedder)
document_search = DocumentSearch(vector_store=vector_store)

llm = LiteLLM(model_name="gpt-4.1-nano")
agent = Agent(llm=llm, tools=[document_search.search])

async def main() -> None:
    await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")
    response = await agent.run("What are the key findings presented in this paper?")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

### Chat UI

To expose your GenAI application through Ragbits API:

```python
from collections.abc import AsyncGenerator
from ragbits.agents import Agent, ToolCallResult
from ragbits.chat.api import RagbitsAPI
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import ChatFormat
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
vector_store = InMemoryVectorStore(embedder=embedder)
document_search = DocumentSearch(vector_store=vector_store)

llm = LiteLLM(model_name="gpt-4.1-nano")
agent = Agent(llm=llm, tools=[document_search.search])

class MyChat(ChatInterface):
    async def setup(self) -> None:
        await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse]:
        async for result in agent.run_streaming(message):
            match result:
                case str():
                    yield self.create_live_update(
                        update_id="1",
                        type=LiveUpdateType.START,
                        label="Answering...",
                    )
                    yield self.create_text_response(result)
                case ToolCall():
                    yield self.create_live_update(
                        update_id="2",
                        type=LiveUpdateType.START,
                        label="Searching...",
                    )
                case ToolCallResult():
                    yield self.create_live_update(
                        update_id="2",
                        type=LiveUpdateType.FINISH,
                        label="Search",
                        description=f"Found {len(result.result)} relevant chunks.",
                    )

        yield self.create_live_update(
            update_id="1",
            type=LiveUpdateType.FINISH,
            label="Answer",
        )

if __name__ == "__main__":
    api = RagbitsAPI(MyChat)
    api.run()
```

## Rapid development

Create Ragbits projects from templates:

```sh
uvx create-ragbits-app
```

Explore `create-ragbits-app` repo [here](https://github.com/deepsense-ai/create-ragbits-app). If you have a new idea for a template, feel free to contribute!

## Documentation

- [Tutorials](https://ragbits.deepsense.ai/stable/tutorials/intro) - Get started with Ragbits in a few minutes
- [How-to](https://ragbits.deepsense.ai/stable/how-to/prompts/use_prompting) - Learn how to use Ragbits in your projects
- [CLI](https://ragbits.deepsense.ai/stable/cli/main) - Learn how to run Ragbits in your terminal
- [API reference](https://ragbits.deepsense.ai/stable/api_reference/core/prompt) - Explore the underlying Ragbits API

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](https://github.com/deepsense-ai/ragbits/tree/main/CONTRIBUTING.md) for more information.

## License

Ragbits is licensed under the [MIT License](https://github.com/deepsense-ai/ragbits/tree/main/LICENSE).
