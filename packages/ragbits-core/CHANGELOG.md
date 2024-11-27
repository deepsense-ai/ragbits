# CHANGELOG

## Unreleased

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
- Introduce core components: Prompts, LLMs, Embeddings and VectorStores.
- `Prompt` class integration with promptfoo.
- LiteLLM integration.
- ChromaDB integration.
- Prompts lab.
- Prompts autodiscovery.

