# Examples

This directory contains example scripts that demonstrate various functionalities of the Ragbits library.
Each script showcases a specific use case, providing a practical guide to using Ragbits components.

## Prerequisites

To run the script, you will need to have `uv` installed.
Some scripts may also require additional dependencies or API keys for external services.

All necessary details are provided in the comments at the top of each script.

## Scripts Overview

### Core (`examples/core/`)

| Script                                                                                 |                    Ragbits Package                    | Description                                                                                                                             |
|:---------------------------------------------------------------------------------------|:-----------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------------------|
| [Text Prompt](/examples/core/prompt/text.py)                                           | [ragbits-core](/packages/ragbits-core)                | Example of how to use the `Prompt` class to generate themed text using an LLM with a simple text prompt.                                |
| [Text Prompt with Few Shots](/examples/core/prompt/text_with_few_shots.py)             | [ragbits-core](/packages/ragbits-core)                | Example of how to use the `Prompt` class to generate themed text using an LLM with a text prompt and few-shot examples.                 |
| [Multimodal Prompt with Image Input](/examples/core/prompt/multimodal_with_image.py)   | [ragbits-core](/packages/ragbits-core)                | Example of how to use the `Prompt` class to generate themed text using an LLM with both text and image inputs.                          |
| [Multimodal Prompt with PDF Input](/examples/core/prompt/multimodal_with_pdf.py)       | [ragbits-core](/packages/ragbits-core)                | Example of how to use the `Prompt` class to answer the question using an LLM with both text and PDF inputs.                             |
| [Multimodal Prompt with Few Shots](/examples/core/prompt/multimodal_with_few_shots.py) | [ragbits-core](/packages/ragbits-core)                | Example of how to use the `Prompt` class to generate themed text using an LLM with multimodal inputs and few-shot examples.             |
| [Tool Use with LLM](/examples/core/llms/tool_use.py)                                   | [ragbits-core](/packages/ragbits-core)                | Example of how to provide tools and return tool calls from LLM.                                                                         |
| [Reasoning with LLM](/examples/core/llms/reasoning.py)                                 | [ragbits-core](/packages/ragbits-core)                | Example of how to use reasoning with LLM.                                                                                               |
| [OpenTelemetry Audit](/examples/core/audit/otel.py)                                    | [ragbits-core](/packages/ragbits-core)                | Example of how to collect traces and metrics using Ragbits audit module with OpenTelemetry.                                             |
| [Logfire Audit](/examples/core/audit/logfire_.py)                                      | [ragbits-core](/packages/ragbits-core)                | Example of how to collect traces and metrics using Ragbits audit module with Logfire.                                                   |

### Document Search (`examples/document-search/`)

| Script                                                                                           |                          Ragbits Package                          | Description                                                                                                                                             |
|:-------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Basic Document Search](/examples/document-search/basic.py)                                      | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` class to search for documents with the `InMemoryVectorStore` class to store the embeddings.                  |
| [Chroma Document Search](/examples/document-search/chroma.py)                                    | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` class to search for documents with the `ChromaVectorStore` class to store the embeddings.                    |
| [Multimodal Document Search](/examples/document-search/multimodal.py)                            | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` to index and search for images and text documents with the `MultimodalEmbedding` from VertexAI.              |
| [PgVector Document Search](/examples/document-search/pgvector.py)                                | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` class to search for documents with the `PgVectorStore` class to store the embeddings in a Postgres database. |
| [Qdrant Document Search](/examples/document-search/qdrant.py)                                    | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` class to search for documents with the `QdrantVectorStore` class to store the embeddings.                    |
| [Weaviate Document Search](/examples/document-search/weaviate_.py)                               | [ragbits-document-search](/packages/ragbits-document-search)      | Example of how to use the `DocumentSearch` class to search for documents with the `WeaviateVectorStore` class to store the embeddings.                  |

### Evaluate (`examples/evaluate/`)

| Script                                                                                           |                    Ragbits Package                    | Description                                                                                              |
|:-------------------------------------------------------------------------------------------------|:-----------------------------------------------------:|:---------------------------------------------------------------------------------------------------------|
| [Dataset Generation](/examples/evaluate/dataset-generator/generate.py)                           | [ragbits-evaluate](/packages/ragbits-evaluate)        | Example of how to generate a synthetic dataset using the `DatasetGenerationPipeline` class.              |
| [Basic Document Search Evaluation](/examples/evaluate/document-search/basic/evaluate.py)         | [ragbits-evaluate](/packages/ragbits-evaluate)        | Example of how to evaluate a basic document search pipeline using the `Evaluator` class.                 |
| [Basic Document Search Optimization](/examples/evaluate/document-search/basic/optimize.py)       | [ragbits-evaluate](/packages/ragbits-evaluate)        | Example of how to optimize a basic document search pipeline using the `Optimizer` class.                 |
| [Advanced Document Search Evaluation](/examples/evaluate/document-search/advanced/evaluate.py)   | [ragbits-evaluate](/packages/ragbits-evaluate)        | Example of how to evaluate an advanced document search pipeline using the `Evaluator` class.             |
| [Advanced Document Search Optimization](/examples/evaluate/document-search/advanced/optimize.py) | [ragbits-evaluate](/packages/ragbits-evaluate)        | Example of how to optimize an advanced document search pipeline using the `Optimizer` class.             |
| [Agent Benchmarking Agents](/examples/evaluate/agent-benchmarking/example_agents.py)             | [ragbits-evaluate](/packages/ragbits-evaluate)        | Agent definitions (HumanEval, HotpotQA, GAIA) for benchmarking with optional planning capabilities.     |

### Chat (`examples/chat/`)

| Script                                                                                  |                 Ragbits Package                  | Description                                                                                                                      |
|:----------------------------------------------------------------------------------------|:------------------------------------------------:|:---------------------------------------------------------------------------------------------------------------------------------|
| [Chat Interface](/examples/chat/chat.py)                                                | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` to create a simple chat application.                                                   |
| [Offline Chat Interface](/examples/chat/offline_chat.py)                                | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` to create a simple chat application that works offline.                                |
| [Authenticated Chat Interface](/examples/chat/authenticated_chat.py)                   | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` with user authentication (credentials, Discord and Google OAuth2).                     |
| [Chat Interface without Summary Generator](/examples/chat/no_summary_generator.py)     | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` without a `SummaryGenerator`.                                                         |
| [Recontextualize Last Message](/examples/chat/recontextualize_message.py)              | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `StandaloneMessageCompressor` compressor to recontextualize the last message in a conversation history.|
| [Stream Events from Tools to Chat](/examples/chat/stream_events_from_tools_to_chat.py) | [ragbits-chat](/packages/ragbits-chat)           | Example of how to stream custom tool events (e.g. charts) from an agent to the chat UI.                                         |
| [Themed Chat Interface](/examples/chat/themed_chat.py)                                  | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` with a custom HeroUI theme.                                                            |
| [Tutorial Chat Interface](/examples/chat/tutorial.py)                                  | [ragbits-chat](/packages/ragbits-chat)           | Full-featured chat with authentication, user settings, feedback, live updates, web search and image generation.                  |
| [Upload Chat Interface](/examples/chat/upload_chat.py)                                  | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` with file upload support via `upload_handler`.                                         |
| [File Explorer Agent](/examples/chat/file_explorer_agent.py)                            | [ragbits-chat](/packages/ragbits-chat)           | Secure file management agent with path validation and confirmation for all file operations within a restricted directory.        |
| [Code Planner](/examples/chat/code_planner.py)                                          | [ragbits-chat](/packages/ragbits-chat)           | Example of how to use the `ChatInterface` with planning tools for code architecture tasks.                                      |

### Agents (`examples/agents/`)

| Script                                                                                          |                Ragbits Package                | Description                                                                                              |
|:------------------------------------------------------------------------------------------------|:---------------------------------------------:|:---------------------------------------------------------------------------------------------------------|
| [Tool Use](/examples/agents/tool_use.py)                                                        |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to use agent with tools.                                                                  |
| [Agent with Decorator](/examples/agents/with_decorator.py)                                      |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to use the `@Agent.prompt_config` decorator to define an agent as a class.               |
| [Agent Dependencies](/examples/agents/dependencies.py)                                          |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to bind dependencies to an agent via `AgentRunContext`.                                   |
| [OpenAI Native Tool Use](/examples/agents/openai_native_tool_use.py)                            |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to use agent with OpenAI native tools.                                                    |
| [Downstream Agent Streaming](/examples/agents/downstream_agents_streaming.py)                   |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to stream outputs from downstream agents in real time.                                    |
| [Streaming Events from Tools](/examples/agents/stream_events_from_tools.py)                     |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to define a tool that emits custom events that can be streamed from an agent.             |
| [CLI Agent](/examples/agents/cli_agent.py)                                                      |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to expose an agent via the ragbits CLI for interactive use.                               |
| [Memory Tool](/examples/agents/memory_tool_example.py)                                          |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to add long-term memory capabilities to an agent using the memory tool. |
| [Agents Planning Tools](/examples/agents/planning.py)                                           |  [ragbits-agents](/packages/ragbits-agents)   | Example of how to use planning tools for task breakdown and sequential execution. |

#### Hooks (`examples/agents/hooks/`)

| Script                                                                                       |                   Ragbits Package                    | Description                                                                                              |
|:---------------------------------------------------------------------------------------------|:----------------------------------------------------:|:---------------------------------------------------------------------------------------------------------|
| [Output Logging](/examples/agents/hooks/agent_output_logging.py)                             | [ragbits-agents](/packages/ragbits-agents)           | Example of using POST_TOOL hooks to log outputs returned by downstream agent tools.                      |
| [Guardrails Integration](/examples/agents/hooks/guardrails_integration.py)                   | [ragbits-agents](/packages/ragbits-agents)           | Example of using PRE_RUN hooks for guardrail-based input validation and ON_EVENT hooks for streaming.    |
| [Validation and Sanitization](/examples/agents/hooks/validation_and_sanitization.py)         | [ragbits-agents](/packages/ragbits-agents)           | Example of using PRE_TOOL and POST_TOOL hooks for argument validation, sanitization, and output masking. |

#### MCP (`examples/agents/mcp/`)

| Script                                                                    |                   Ragbits Package                    | Description                                                                             |
|:--------------------------------------------------------------------------|:----------------------------------------------------:|:----------------------------------------------------------------------------------------|
| [MCP Local](/examples/agents/mcp/local.py)                                | [ragbits-agents](/packages/ragbits-agents)           | Example of how to use the `Agent` class to connect with a local MCP server.             |
| [MCP SSE](/examples/agents/mcp/sse.py)                                    | [ragbits-agents](/packages/ragbits-agents)           | Example of how to use the `Agent` class to connect with a remote MCP server via SSE.   |
| [MCP Streamable HTTP](/examples/agents/mcp/streamable_http.py)            | [ragbits-agents](/packages/ragbits-agents)           | Example of how to use the `Agent` class to connect with a remote MCP server via HTTP.  |

#### A2A (`examples/agents/a2a/`)

| Script                                                                                                    |                   Ragbits Package                    | Description                                                                                                             |
|:----------------------------------------------------------------------------------------------------------|:----------------------------------------------------:|:------------------------------------------------------------------------------------------------------------------------|
| [Flight Agent](/examples/agents/a2a/flight_agent.py)                                                      | [ragbits-agents](/packages/ragbits-agents)           | A2A-compatible agent that returns available flights between two cities; used as a remote sub-agent in orchestration examples. |
| [Hotel Agent](/examples/agents/a2a/hotel_agent.py)                                                        | [ragbits-agents](/packages/ragbits-agents)           | A2A-compatible agent that recommends hotels for a given city; used as a remote sub-agent in orchestration examples.          |
| [City Explorer Agent](/examples/agents/a2a/city_explorer_agent.py)                                        | [ragbits-agents](/packages/ragbits-agents)           | A2A-compatible agent that fetches and summarizes city information from Wikipedia using an MCP fetch server.                  |
| [Agent Orchestrator](/examples/agents/a2a/agent_orchestrator.py)                                          | [ragbits-agents](/packages/ragbits-agents)           | A custom `AgentOrchestrator` class that coordinates multiple remote A2A agents; imported by the orchestration examples.     |
| [A2A Orchestration](/examples/agents/a2a/run_orchestrator.py)                                             | [ragbits-agents](/packages/ragbits-agents)           | Example of how to set up an A2A orchestration using a custom `AgentOrchestrator` class that routes tasks to remote agents.  |
| [A2A Orchestration with Tools](/examples/agents/a2a/agent_orchestrator_with_tools.py)                     | [ragbits-agents](/packages/ragbits-agents)           | Example of how to set up an A2A orchestrator that routes tasks to remote agents using tools, with streamed output.          |
