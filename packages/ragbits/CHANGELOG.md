# CHANGELOG

## Unreleased

### Changed

- Introduce ruff as linter and code formatter (#87).

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
