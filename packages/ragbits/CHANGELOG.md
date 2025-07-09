# CHANGELOG

## Unreleased

## 1.1.0 (2025-07-09)


### 🤖 Agent Release

This release brings agentic capabilities to Ragbits, together with major user interface enhancements, expanded observability, new integrations, and core improvements.

### ✨ Key Features & Highlights

#### Agents: Easily build agentic systems that proactively interact with their environment.

- **Agent Interface:** Define agents by combining LLMs, prompts, and tools using the `ragbits-agents` package. Tool creation is streamlined—simply annotate Python functions, and Ragbits automatically handles type hints and docstrings for agent consumption.
- **MCP Server Integration:** Connect your agents to hundreds of off-the-shelf tools by running or connecting to an MCP Server, instantly expanding agent capabilities.
- **A2A Protocol Support:** Enable inter-agent communication with the new A2A Protocol. The `Agent.to_a2a()` method makes it seamless to register an agent as an A2A Card, share, and communicate via the bundled A2A Server.
- **Streaming Responses:** All agents now support streaming by default—use `Agent.run_streaming()` to send results as they’re generated, improving responsiveness and UX.
- **Tracing & Observability:** Built-in agent tracing support with multiple backends including OpenTelemetry, CLI, and Logfire, making it easy to monitor and debug agent reasoning and tool use.

#### Ragbits UI Improvements
- **User Interface Improvements:** Richer, more interactive and customizable chat experiences.
- **Live Updates:** Real-time notifications from the backend keep users in the loop—see searches, tool calls, and step-by-step reasoning as they happen.
- **Message History Navigation:** Use up/down arrows to effortlessly navigate and edit previous messages, streamlining user interactions.
- **Follow-up Message Suggestions:** Applications can now suggest contextual follow-up questions. Show follow-up buttons in the UI by simply calling a backend method.
- **TypeScript SDK:** Faster custom integrations! Access Ragbits API from your own interfaces using the new TypeScript SDK, available standalone or as React hooks.
- **User Settings:** Define a Pydantic model to automatically generate a user settings form in the UI. These settings can customize chatbot behavior per-user—making it simple to add personalizable controls.
- **Debug Mode:** Activate debug mode in the chat UI to view internal chat state, events, and other chatbot internals, greatly aiding development and troubleshooting.

#### Observability
- **Comprehensive OpenTelemetry Metrics:** Now supporting all OpenTelemetry metric types for robust, expressive monitoring.
- **Server Observability:** Improved observability into servers registered or available through RagbitsAPI, surfacing infrastructure insights.
- **Grafana Dashboards:** New, ready-to-use Grafana dashboards are now bundled with `create-ragbits-app` for instant monitoring out of the box.
- **Logfire Integration:** One-line setup to send traces and metrics directly to Pydantic Logfire, enabling comprehensive observability with minimal configuration.

#### Integrations
- **Weaviate VectorStore:** Use Weaviate as a fully compatible VectorStore backend across Ragbits components such as document-search.

#### Developer Experience & Other Improvements
- **RagbitsChatClient:** Introduced a new `RagbitsChatClient` for seamless interaction with RagbitsAPI from Python. Makes building custom python clients and integrations easier than ever.


## 1.0.0 (2025-06-04)

### 🎉 Major Release

This is the first stable release of ragbits, marking a significant milestone in the project's development.
The v1.0.0 release represents a mature, production-ready framework for building GenAI applications.

### 🚀 New Features

#### ragbits-core
- **Vector Store Improvements**:
  - Automatic vector_size resolution by PgVectorStore
  - Added get_vector_size method to all Embedders
  - Added support for limiting VectorStore results by metadata
- **Embeddings**: Refactored BagOfTokens model with model_name/encoding_name parameters moved to init
- **Type Safety**: Renamed typevars InputT and OutputT to PromptInputT and PromptOutputT for better clarity
- **Monitoring**: Added Prometheus & Grafana monitoring for LLMs using OpenTelemetry
- **File Type Detection**: Switched from imghdr to filetype for image file type detection
- **Utilities**: Added batched() helper method to utils

#### ragbits-document-search
- **Advanced Document Processing**: Switch to docling as default document parser for improved document handling
- **Batching Support**: Added elements batching for ingest strategies to improve performance
- **Document Types**: Added support for JSONL file type and improved document file type detection
- **Reranking Enhancements**:
  - Added LLM reranker with optional score override
  - Added score threshold to reranker options
  - Retained score information from vector database or reranker in Element class
- **Query Processing**: Added query rephraser options for better search results
- **Error Handling**: Improved error handling for elements without enricher

#### ragbits-chat
- **Persistence Support**: Added persistence component to save chat interactions from ragbits-chat with conversation_id parameter support
- **State Management**: Added support for state updates in chat interfaces with automatic signature generation
- **UI Improvements**: Refactored UI components to allow modifications and rebuilt UI with new dependencies
- **API Integration**: Enhanced API integration with history context changes and feedback form integration

#### ragbits-evaluate
- **Question Answering**: Added evaluations for question answering tasks
- **Dataset Enhancements**:
  - Added support for slicing datasets
  - Support for custom column names in evaluation datasets
  - Support for reference document ids and page numbers
- **Batch Processing**: Adjusted evaluation pipeline interface to support batch processing
- **Data Loading**: Separated load and map operations in data loaders


## 0.20.1 (2025-06-04)

### Changed

- ragbits-chat updated to version v0.20.1
- ragbits-cli updated to version v0.20.1
- ragbits-document-search updated to version v0.20.1
- ragbits-evaluate updated to version v0.20.1
- ragbits-guardrails updated to version v0.20.1
- ragbits-core updated to version v0.20.1

## 0.20.0 (2025-06-03)

### Changed

- ragbits-chat updated to version v0.20.0
- ragbits-cli updated to version v0.20.0
- ragbits-document-search updated to version v0.20.0
- ragbits-evaluate updated to version v0.20.0
- ragbits-guardrails updated to version v0.20.0
- ragbits-core updated to version v0.20.0

## 0.19.1 (2025-05-27)

### Changed

- ragbits-chat updated to version v0.19.1
- ragbits-cli updated to version v0.19.1
- ragbits-document-search updated to version v0.19.1
- ragbits-evaluate updated to version v0.19.1
- ragbits-guardrails updated to version v0.19.1
- ragbits-core updated to version v0.19.1

## 0.19.0 (2025-05-27)

### Changed

- ragbits-chat updated to version v0.19.0
- ragbits-cli updated to version v0.19.0
- ragbits-document-search updated to version v0.19.0
- ragbits-evaluate updated to version v0.19.0
- ragbits-guardrails updated to version v0.19.0
- ragbits-core updated to version v0.19.0

## 0.18.0 (2025-05-22)

### Changed

- ragbits-chat updated to version v0.18.0
- ragbits-cli updated to version v0.18.0
- ragbits-document-search updated to version v0.18.0
- ragbits-evaluate updated to version v0.18.0
- ragbits-guardrails updated to version v0.18.0
- ragbits-core updated to version v0.18.0

## 0.17.1 (2025-05-09)

### Changed

- ragbits-chat updated to version v0.17.1
- ragbits-cli updated to version v0.17.1
- ragbits-document-search updated to version v0.17.1
- ragbits-evaluate updated to version v0.17.1
- ragbits-guardrails updated to version v0.17.1
- ragbits-core updated to version v0.17.1

## 0.17.0 (2025-05-06)

### Changed

- ragbits-chat updated to version v0.17.0
- ragbits-cli updated to version v0.17.0
- ragbits-document-search updated to version v0.17.0
- ragbits-evaluate updated to version v0.17.0
- ragbits-guardrails updated to version v0.17.0
- ragbits-core updated to version v0.17.0

## 0.16.0 (2025-04-29)

### Changed

- ragbits-chat updated to version v0.16.0
- ragbits-cli updated to version v0.16.0
- ragbits-document-search updated to version v0.16.0
- ragbits-evaluate updated to version v0.16.0
- ragbits-guardrails updated to version v0.16.0
- ragbits-core updated to version v0.16.0

## 0.15.0 (2025-04-28)

### Changed

- ragbits-chat updated to version v0.15.0
- ragbits-cli updated to version v0.15.0
- ragbits-document-search updated to version v0.15.0
- ragbits-evaluate updated to version v0.15.0
- ragbits-guardrails updated to version v0.15.0
- ragbits-core updated to version v0.15.0

## 0.14.0 (2025-04-22)

### Changed

- ragbits-chat updated to version v0.14.0
- ragbits-cli updated to version v0.14.0
- ragbits-document-search updated to version v0.14.0
- ragbits-evaluate updated to version v0.14.0
- ragbits-guardrails updated to version v0.14.0
- ragbits-core updated to version v0.14.0

## 0.13.0 (2025-04-02)

### Changed

- ragbits-cli updated to version v0.13.0
- ragbits-conversations updated to version v0.13.0
- ragbits-document-search updated to version v0.13.0
  - DocumentSearch.ingest now raises IngestExecutionError when any errors are encountered during ingestion.
- ragbits-evaluate updated to version v0.13.0
- ragbits-guardrails updated to version v0.13.0
- ragbits-core updated to version v0.13.0
  - Make the score in VectorStoreResult consistent (always bigger is better)
  - Add router option to LiteLLMEmbedder (#440)
  - Make LLM / Embedder APIs consistent (#463)
  - New methods in Prompt class for appending conversation history (#480)
  - Fix: make unflatten_dict symmetric to flatten_dict (#461)
  - Cost and capabilities config for custom litellm models (#481)

## 0.12.0 (2025-03-25)

### Changed

- ragbits-cli updated to version v0.12.0
- ragbits-conversations updated to version v0.12.0
- ragbits-document-search updated to version v0.12.0
  - BREAKING CHANGE: Providers and intermediate handlers refactored to parsers and enrichers (#419)
- ragbits-evaluate updated to version v0.12.0
- ragbits-guardrails updated to version v0.12.0
- ragbits-core updated to version v0.12.0
  - Allow Prompt class to accept the asynchronous response_parser. Change the signature of parse_response method.
  - Fix from_config for LiteLLM class (#441)
  - Fix Qdrant vector store serialization (#419)

## 0.11.0 (2025-03-25)

### Changed

- ragbits-cli updated to version v0.11.0
- ragbits-conversations updated to version v0.11.0
- ragbits-document-search updated to version v0.11.0
  - Introduce picklable ingest error wrapper (#448)
  - Add support for Git source to fetch files from Git repositories (#439)
- ragbits-evaluate updated to version v0.11.0
- ragbits-guardrails updated to version v0.11.0
- ragbits-core updated to version v0.11.0
  - Add HybridSearchVectorStore which can aggregate results from multiple VectorStores (#412)

## 0.10.2 (2025-03-21)

### Changed

- ragbits-cli updated to version v0.10.2
- ragbits-conversations updated to version v0.10.2
- ragbits-document-search updated to version v0.10.2
  - Remove obsolete ImageDescriber and llm from UnstructuredImageProvider (#430)
  - Make SourceError and its subclasses picklable (#435)
  - Allow for setting custom headers in WebSource (#437)
- ragbits-evaluate updated to version v0.10.2
- ragbits-guardrails updated to version v0.10.2
- ragbits-core updated to version v0.10.2

## 0.10.1 (2025-03-19)

### Changed

- ragbits-cli updated to version v0.10.1
- ragbits-conversations updated to version v0.10.1
- ragbits-document-search updated to version v0.10.1
  - BREAKING CHANGE: Renamed HttpSource to WebSource and changed property names (#420)
  - Better error distinction for WebSource (#421)
- ragbits-evaluate updated to version v0.10.1
- ragbits-guardrails updated to version v0.10.1
- ragbits-core updated to version v0.10.1
  - Better handling of cases when text and image embeddings are mixed in VectorStore

## 0.10.0 (2025-03-17)

### Changed

- ragbits-cli updated to version v0.10.0
- ragbits-conversations updated to version v0.10.0
- ragbits-document-search updated to version v0.10.0
  - BREAKING CHANGE: Processing strategies refactored to ingest strategies (#394)
  - Compability with the new Vector Store interface from ragbits-core (#288)
  - Fix docstring formatting to resolve Griffe warnings
  - Introduce intermediate image elements (#139)
  - Add HTTP source type, which downloads a file from the provided URL (#397)
  - added traceable
- ragbits-evaluate updated to version v0.10.0
  - Compability with the new Vector Store interface from ragbits-core (#288)
  - chore: fix typo in README.
  - fix typos in doc strings
- ragbits-guardrails updated to version v0.10.0
- ragbits-core updated to version v0.10.0
  - BREAKING CHANGE: Vector Stores are now responsible for creating embeddings (#288)
  - Qdrant vector store can now be serialized during Ray processing (#394)
  - Improve cli trace handler
  - Add traceable to some method
  - Add support for images in few shot prompts (#155)
  - Add instruction on how to use local servers for LLMs (#395).
  - Introduce intermediate image elements (#139)
  - Correct typos in doc strings (#398)
  - Enable GPU support and (un)pickling for fastembed embedders (#409).

## 0.9.0 (2025-02-25)

### Changed

- ragbits-cli updated to version v0.9.0
- ragbits-conversations updated to version v0.9.0
  - Add support to persisting history of conversations using sqlalchemy (#354).
- ragbits-document-search updated to version v0.9.0
  - Add MultiQueryRetrieval (#311).
  - Add AWS S3 source integration (#339).
  - Add Azure BlobStorage source integration (#340).
- ragbits-evaluate updated to version v0.9.0
  - Add cli for document search evaluation added (#356)
  - Add local data loader (#334).
- ragbits-guardrails updated to version v0.9.0
- ragbits-core updated to version v0.9.0
  - Add support to fastembed dense & sparse embeddings.
  - Rename "default configuration" to "preferred configuration" (#361).
  - Allow to pass str or dict to LLM.generate() (#286)
  - Fix: changed variable type from Filter to WhereQuery in the Qdrant vector store in list method.
  - Rename all embedders to have `Embedder` in their name (instead of `Embeddings`).

## 0.8.0 (2025-01-29)

### Added

- ragbits-document-search updated to version v0.8.0
  - DocumentSearch ingest accepts now a simple string format to determine sources; for example gcs://bucket/* (#264).
  - New CLI command to ingest documents (#305).
  - Add support for rerankers library (#284).
- ragbits-core updated to version v0.8.0
  - Add support for pgvector as VectorStore (#267).

### Changed

- ragbits-cli updated to version v0.8.0
- ragbits-conversations updated to version v0.8.0
- ragbits-evaluate updated to version v0.8.0
- ragbits-guardrails updated to version v0.8.0

## 0.7.0 (2025-01-21)

### Added

- ragbits-document-search updated to version v0.7.0
  - Add CLI command to perform search on DocumentSearch instance (#290).
- ragbits-core updated to version v0.7.0
  - Add nice-looking CLI logging for audit module (#273).
  - Add support for returning metadata from LLMs (#274).

### Changed

- ragbits-cli updated to version v0.7.0
- ragbits-conversations updated to version v0.7.0
  - Added last message recontextualization (#271).
- ragbits-document-search updated to version v0.7.0
  - New way to initialize DocumentSearch instances (#277).
- ragbits-evaluate updated to version v0.7.0
  - Simplified interface to document-search evaluation (#258).
- ragbits-guardrails updated to version v0.7.0
- ragbits-core updated to version v0.7.0
  - Fix: limiting in qdrant vector store (#282).
  - Refactor: remove LLM client abstraction and lift it up to LLM (#270).

## 0.6.0 (2024-12-27)

### Added

- ragbits-cli updated to version v0.6.0
  - Better error handling when dynamic importing fails in the CLI (#259).
  - Add option to choose what columns to display in the output (#257).
- ragbits-core updated to version v0.6.0
  - Add option to pass LiteLLM router to LLM instances (#262).
  - Add commands to browse vector stores (#244).

### Changed

- ragbits-core updated to version v0.6.0
  - Implement generic Options class (#248).
  - Fix LiteLLM crash in python 3.13 (#245).
- ragbits-document-search updated to version v0.6.0
- ragbits-evaluate updated to version v0.6.0
- ragbits-guardrails updated to version v0.6.0

## 0.5.1 (2024-12-09)

### Changed

- ragbits-cli updated to version v0.5.1
- ragbits-document-search updated to version v0.5.1
- ragbits-evaluate updated to version v0.5.1
  - Document search evaluation now returns all Element types, rather than only TextElements (#241).
- ragbits-guardrails updated to version v0.5.1
- ragbits-core updated to version v0.5.1
  - Refactor: added standardized way to create ragbits objects from config (#233).

## 0.5.0 (2024-12-05)

### Added

- ragbits-cli updated to version v0.5.0
  - Add global flag to specify output type: text or json (#232).
- ragbits-document-search updated to version v0.5.0
  - Distributed ingestion with usage of https://www.ray.io/ (#207)
  - Documents can be now replaced in existing VectorStore (#210)
  - Providers are now loaded dynamically (#219)
- ragbits-core updated to version v0.5.0
  - Default LLM factory when configuration is not provided (#209).
  - Add remove operation to VectorStore (#210).
  - Install litellm package by default (#236).

### Changed

- ragbits-evaluate updated to version v0.5.0
- ragbits-guardrails updated to version v0.5.0

## 0.4.0 (2024-11-27)

### Added

- ragbits-document-search updated to version v0.4.0
  - Add support for batch ingestion (#185).
  - Ingesting images is now supported (#172).
- ragbits-evaluate updated to version v0.4.0
  - Introduced optimization with optuna (#177).
  - Add synthetic data generation pipeline (#165).
- ragbits-core updated to version v0.4.0
  - Add support for Qdrant VectorStore (#163).
  - Add streaming interface to LLMs (#188).
  - Better images support in Prompt abstractions (#201).

### Changed

- ragbits-cli updated to version v0.4.0
- ragbits-guardrails updated to version v0.4.0

## 0.3.0 (2024-11-06)

### Added

- ragbits-guardrails v0.3.0:
  - Initial release of the package (#169).
  - First guardrail with OpenAI Moderation.
- ragbits-document-search updated to version v0.3.0
  - Add location metadata to documents ingested into DocumentSearch (#122).
  - Add LiteLLM Reranker (#109).
- ragbits-core updated to version v0.3.0
  - Observability toolset, with initial support to export traces to OpenTelemetry (#168)
  - CLI commands to render / exec prompts (#146)
  - Support of images in Prompt abstractions (#149)
  - Support for different MetadataStores in VectorStore (#144)
  - Now LLMs can be configured separately for vision, text and structured. (#153)

### Changed

- ragbits-cli updated to version v0.3.0
- ragbits-document-search updated to version v0.3.0
  - refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
  - refactor: change the type in from_source method to Source (#156).
  - refactor: unified API for text representations of Element models (#171).
- ragbits-evaluate updated to version v0.3.0
- ragbits-core updated to version v0.3.0
  - refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
  - refactor: Refactor vector store public API. (#151)

## 0.2.0 (2024-10-23)

### Added

- ragbits-evaluate v0.2.0:
  - Initial release of the package (#91).
  - Evaluation pipeline framework with capability to define evaluators & metrics.
  - Evaluation pipeline for `ragbits-document-search`.
- ragbits-document-search updated to version v0.2.0
  - Creation of DocumentSearch instances from config (#62).
  - Automatic detection of document type (#99).
  - LLM-based query rephrasing (#115).
  - Batch ingestion from sources (#112).
  - Support to image formats (#121).
  - HuggingFace sources (#106).
- ragbits-core updated to version v0.2.0
  - Project README.md (#103).
  - Listing entries API for VectorStores (#138).
  - Overrides for prompt discovery configurable in `pyproject.toml` file (#101).
  - Default LLM factory configurable in `pyproject.toml` file (#101).

### Changed

- ragbits-cli updated to version v0.2.0
  - Improved performance by lazy-loading the modules (#111 #113 #120)
- ragbits-core updated to version v0.2.0
  - Fixed bug in chromadb while returning multiple records (#117).
  - Fixed bug in prompt rendering for some pydantic models (#137).

## 0.1.0 (2024-10-08)

### Added

- ragbits-core v0.1.0:
  - Initial release of the package.
  - Introduce core components: Prompts, LLMs, Embeddings and VectorStores.
  - `Prompt` class integration with promptfoo.
  - LiteLLM integration.
  - ChromaDB integration.
  - Prompts lab.
  - Prompts autodiscovery.

- ragbits-cli v0.1.0:
  - Initial release of the package.
  - Add prompts lab command.
  - Add prompts generate-promptfoo-configs command.

- ragbits-document-search v0.1.0:
  - Initial release of the package.
  - Introduce core modules: documents, ingestion and retrival.
  - Unstructured integration.
