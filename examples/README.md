# Examples

This directory contains example scripts that demonstrate various functionalities of the Ragbits library.
Each script showcases a specific use case, providing a practical guide to using Ragbits components.

## Prerequisites

To run the script, you will need to have `uv` installed. Some scripts may also require additional dependencies or API
keys for external services.
All necessary details are provided in the comments at the top of each script.

## Scripts Overview

| Example                                                                                         |     Ragbits Package     | Description                                                                                                                                             |
|:------------------------------------------------------------------------------------------------|:-----------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Agents Tool Use](examples/agents/tool_use.py)                                                  |     ragbits-agents      | Example of how to use agent with tools.                                                                                                                 |
| [Chat Interface](examples/chat/chat.py)                                                         |      ragbits-chat       | Example of how to use the `ChatInterface` to create a simple chat application.                                                                          |
| [Offline Chat Interface](examples/chat/offline_chat.py)                                         |      ragbits-chat       | Example of how to use the `ChatInterface` to create a simple chat application that works offline.                                                       |
| [Recontextualize Last Message](examples/chat/recontextualize_message.py)                        |      ragbits-chat       | Example of how to use the `StandaloneMessageCompressor` compressor to recontextualize the last message in a conversation history.                       |
| [Logfire Audit](examples/core/audit/logfire_.py)                                                |      ragbits-core       | Example of how to collect traces and metrics using Ragbits audit module with Logfire.                                                                   |
| [OpenTelemetry Audit](examples/core/audit/otel.py)                                              |      ragbits-core       | Example of how to collect traces and metrics using Ragbits audit module with OpenTelemetry.                                                             |
| [Tool Use with LLM](examples/core/llms/tool_use.py)                                             |      ragbits-core       | Example of how to provide tools and return tool calls from LLM.                                                                                         |
| [Multimodal Prompt](examples/core/prompt/multimodal.py)                                         |      ragbits-core       | Example of how to use the `Prompt` class to generate themed text using an LLM with both text and image inputs.                                          |
| [Multimodal Prompt with Few Shots](examples/core/prompt/multimodal_with_few_shots.py)           |      ragbits-core       | Example of how to use the `Prompt` class to generate themed text using an LLM with multimodal inputs and few-shot examples.                             |
| [Text Prompt](examples/core/prompt/text.py)                                                     |      ragbits-core       | Example of how to use the `Prompt` class to generate themed text using an LLM with a simple text prompt.                                                |
| [Text Prompt with Few Shots](examples/core/prompt/text_with_few_shots.py)                       |      ragbits-core       | Example of how to use the `Prompt` class to generate themed text using an LLM with a text prompt and few-shot examples.                                 |
| [Basic Document Search](examples/document-search/basic.py)                                      | ragbits-document-search | Example of how to use the `DocumentSearch` class to search for documents with the `InMemoryVectorStore` class to store the embeddings.                  |
| [Chroma Document Search](examples/document-search/chroma.py)                                    | ragbits-document-search | Example of how to use the `DocumentSearch` class to search for documents with the `ChromaVectorStore` class to store the embeddings.                    |
| [Multimodal Document Search](examples/document-search/multimodal.py)                            | ragbits-document-search | Example of how to use the `DocumentSearch` to index and search for images and text documents with the `MultimodalEmbedding` from VertexAI.              |
| [PgVector Document Search](examples/document-search/pgvector.py)                                | ragbits-document-search | Example of how to use the `DocumentSearch` class to search for documents with the `PgVectorStore` class to store the embeddings in a Postgres database. |
| [Qdrant Document Search](examples/document-search/qdrant.py)                                    | ragbits-document-search | Example of how to use the `DocumentSearch` class to search for documents with the `QdrantVectorStore` class to store the embeddings.                    |
| [Dataset Generation](examples/evaluate/dataset-generator/generate.py)                           |    ragbits-evaluate     | Example of how to generate a synthetic dataset using the `DatasetGenerationPipeline` class.                                                             |
| [Advanced Document Search Evaluation](examples/evaluate/document-search/advanced/evaluate.py)   |    ragbits-evaluate     | Example of how to evaluate an advanced document search pipeline using the `Evaluator` class.                                                            |
| [Advanced Document Search Optimization](examples/evaluate/document-search/advanced/optimize.py) |    ragbits-evaluate     | Example of how to optimize an advanced document search pipeline using the `Optimizer` class.                                                            |
| [Basic Document Search Evaluation](examples/evaluate/document-search/basic/evaluate.py)         |    ragbits-evaluate     | Example of how to evaluate a basic document search pipeline using the `Evaluator` class.                                                                |
| [Basic Document Search Optimization](examples/evaluate/document-search/basic/optimize.py)       |    ragbits-evaluate     | Example of how to optimize a basic document search pipeline using the `Optimizer` class.                                                                |