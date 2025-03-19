# CHANGELOG

## Unreleased

## 0.10.1 (2025-03-19)

### Changed

- ragbits-cli updated to version v0.10.1
- ragbits-conversations updated to version v0.10.1
- ragbits-document-search updated to version v0.10.1
- ragbits-evaluate updated to version v0.10.1
- ragbits-guardrails updated to version v0.10.1
- ragbits-core updated to version v0.10.1

## 0.10.0 (2025-03-17)

### Changed

- ragbits-cli updated to version v0.10.0
- ragbits-conversations updated to version v0.10.0
- ragbits-document-search updated to version v0.10.0
- ragbits-evaluate updated to version v0.10.0
- ragbits-guardrails updated to version v0.10.0
- ragbits-core updated to version v0.10.0

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
  - Rename "default configuration" to "preferred configuration" (#361).
  - Allow to pass str or dict to LLM.generate() (#286)
  - Fix: changed variable type from Filter to WhereQuery in the Qdrant vector store in list method.


## 0.8.0 (2025-01-29)

### Changed

- ragbits-cli updated to version v0.8.0
- ragbits-conversations updated to version v0.8.0
- ragbits-document-search updated to version v0.8.0
  - DocumentSearch ingest accepts now a simple string format to determine sources; for example gcs://bucket/* (#264).
  - New CLI command to ingest documents (#305).
  - Add support for rerankers library (#284).
- ragbits-evaluate updated to version v0.8.0
- ragbits-guardrails updated to version v0.8.0
- ragbits-core updated to version v0.8.0
  - Add support for pgvector as VectorStore (#267).

## 0.7.0 (2025-01-21)

### Changed

- ragbits-cli updated to version v0.7.0
- ragbits-conversations updated to version v0.7.0
  - Added last message recontextualization (#271).
- ragbits-document-search updated to version v0.7.0
  - Add CLI command to perform search on DocumentSearch instance (#290).
  - New way to initialize DocumentSearch instances (#277).
  - ragbits-core updated to version v0.7.0
- ragbits-evaluate updated to version v0.7.0
  - Simplified interface to document-search evaluation (#258).
- ragbits-guardrails updated to version v0.7.0
- ragbits-core updated to version v0.7.0
  - Add nice-looking CLI logging for audit module (#273).
  - Add support for returning metadata from LLMs (#274).
  - Fix: limiting in qdrant vector store (#282).
  - Refactor: remove LLM client abstraction and lift it up to LLM (#270).

## 0.6.0 (2024-12-27)

### Changed

- ragbits-cli updated to version v0.6.0
  - Better error handling when dynamic importing fails in the CLI (#259).
  - Add option to choose what columns to display in the output (#257).
- ragbits-core updated to version v0.6.0
  - Add option to pass LiteLLM router to LLM instances (#262).
  - Add commands to browse vector stores (#244).
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

### Changed

- ragbits-cli updated to version v0.5.0
  - Add global flag to specify output type: text or json (#232).
- ragbits-document-search updated to version v0.5.0
  - Distributed ingestion with usage of https://www.ray.io/ (#207)
  - Documents can be now replaced in existing VectorStore (#210)
  - Providers are now loaded dynamically (#219)
- ragbits-evaluate updated to version v0.5.0
- ragbits-guardrails updated to version v0.5.0
- ragbits-core updated to version v0.5.0
  - Default LLM factory when configuration is not provided (#209).
  - Add remove operation to VectorStore (#210).
  - Install litellm package by default (#236).

## 0.4.0 (2024-11-27)

### Changed

- ragbits-cli updated to version v0.4.0
- ragbits-document-search updated to version v0.4.0
  - Add support for batch ingestion (#185).
  - Ingesting images is now supported (#172).
- ragbits-evaluate updated to version v0.4.0
  - Introduced optimization with optuna (#177).
  - Add synthetic data generation pipeline (#165).
- ragbits-guardrails updated to version v0.4.0
- ragbits-core updated to version v0.4.0
  - Add support for Qdrant VectorStore (#163).
  - Add streaming interface to LLMs (#188).
  - Better images support in Prompt abstractions (#201).

## 0.3.0 (2024-11-06)

### Added

- ragbits-guardrails v0.3.0:
  - Initial release of the package (#169).
  - First guardrail with OpenAI Moderation.

### Changed

- ragbits-cli updated to version v0.3.0
- ragbits-document-search updated to version v0.3.0
  - Add location metadata to documents ingested into DocumentSearch (#122).
  - Add LiteLLM Reranker (#109).
  - ragbits-core updated to version v0.3.0
  - refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
  - refactor: change the type in from_source method to Source (#156).
  - refactor: unified API for text representations of Element models (#171).
- ragbits-evaluate updated to version v0.3.0
- ragbits-core updated to version v0.3.0
  - Observability toolset, with initial support to export traces to OpenTelemetry (#168)
  - CLI commands to render / exec prompts (#146)
  - Support of images in Prompt abstractions (#149)
  - Support for different MetadataStores in VectorStore (#144)
  - Now LLMs can be configured separately for vision, text and structured. (#153)
  - refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
  - refactor: Refactor vector store public API. (#151)

## 0.2.0 (2024-10-23)

### Added

- ragbits-evaluate v0.2.0:
  - Initial release of the package (#91).
  - Evaluation pipeline framework with capability to define evaluators & metrics.
  - Evaluation pipeline for `ragbits-document-search`.

### Changed

- ragbits-cli updated to version v0.2.0
  - Improved performance by lazy-loading the modules (#111 #113 #120)
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
