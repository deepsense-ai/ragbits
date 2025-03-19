# CHANGELOG

## Unreleased

## 0.10.1 (2025-03-19)
- Better handling of cases when text and image embeddings are mixed in VectorStore

## 0.10.0 (2025-03-17)

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

- Add support to fastembed dense & sparse embeddings.
- Rename "default configuration" to "preferred configuration" (#361).
- Allow to pass str or dict to LLM.generate() (#286)
- Fix: changed variable type from Filter to WhereQuery in the Qdrant vector store in list method.
- Rename all embedders to have `Embedder` in their name (instead of `Embeddings`).

## 0.8.0 (2025-01-29)

### Added

- Add support for pgvector as VectorStore (#267).

## 0.7.0 (2025-01-21)

### Added

- Add nice-looking CLI logging for audit module (#273).
- Add support for returning metadata from LLMs (#274).

### Changed

- Fix: limiting in qdrant vector store (#282).
- Refactor: remove LLM client abstraction and lift it up to LLM (#270).

## 0.6.0 (2024-12-27)

### Added

- Add option to pass LiteLLM router to LLM instances (#262).
- Add commands to browse vector stores (#244).

### Changed

- Implement generic Options class (#248).
- Fix LiteLLM crash in python 3.13 (#245).

## 0.5.1 (2024-12-09)

### Changed

- Refactor: added standardized way to create ragbits objects from config (#233).

## 0.5.0 (2024-12-05)

### Added

- Default LLM factory when configuration is not provided (#209).
- Add remove operation to VectorStore (#210).
- Install litellm package by default (#236).

## 0.4.0 (2024-11-27)

### Added

- Add support for Qdrant VectorStore (#163).
- Add streaming interface to LLMs (#188).
- Better images support in Prompt abstractions (#201).


## 0.3.0 (2024-11-06)

### Added

- Observability toolset, with initial support to export traces to OpenTelemetry (#168)
- CLI commands to render / exec prompts (#146)
- Support of images in Prompt abstractions (#149)
- Support for different MetadataStores in VectorStore (#144)
- Now LLMs can be configured separately for vision, text and structured. (#153)

### Changed

- refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
- refactor: Refactor vector store public API. (#151)

## 0.2.0 (2024-10-23)

### Added

- Project README.md (#103).
- Listing entries API for VectorStores (#138).
- Overrides for prompt discovery configurable in `pyproject.toml` file (#101).
- Default LLM factory configurable in `pyproject.toml` file (#101).

### Changed

- Fixed bug in chromadb while returning multiple records (#117).
- Fixed bug in prompt rendering for some pydantic models (#137).

## 0.1.0 (2024-10-08)

### Added

- Initial release of the package.
- Introduce core components: Prompts, LLMs, Embedder and VectorStores.
- `Prompt` class integration with promptfoo.
- LiteLLM integration.
- ChromaDB integration.
- Prompts lab.
- Prompts autodiscovery.

