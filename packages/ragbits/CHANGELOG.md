# CHANGELOG

## Unreleased

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
