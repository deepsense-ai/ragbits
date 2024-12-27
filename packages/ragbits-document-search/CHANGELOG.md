# CHANGELOG

## Unreleased

## 0.6.0 (2024-12-27)

### Changed

- ragbits-core updated to version v0.6.0

## 0.5.1 (2024-12-09)

### Changed

- ragbits-core updated to version v0.5.1

## 0.5.0 (2024-12-05)

### Added

- Distributed ingestion with usage of https://www.ray.io/ (#207)
- Documents can be now replaced in existing VectorStore (#210)

### Changed

- ragbits-core updated to version v0.5.0
- Providers are now loaded dynamically (#219)

## 0.4.0 (2024-11-27)

### Added

- Add support for batch ingestion (#185).
- Ingesting images is now supported (#172).

### Changed

- ragbits-core updated to version v0.4.0

## 0.3.0 (2024-11-06)

### Added

- Add location metadata to documents ingested into DocumentSearch (#122).
- Add LiteLLM Reranker (#109).


### Changed

- ragbits-core updated to version v0.3.0
- refactor: Add dynamic loading for modules that depend on optional dependencies (#148).
- refactor: change the type in from_source method to Source (#156).
- refactor: unified API for text representations of Element models (#171).

## 0.2.0 (2024-10-23)

### Added

- Creation of DocumentSearch instances from config (#62).
- Automatic detection of document type (#99).
- LLM-based query rephrasing (#115).
- Batch ingestion from sources (#112).
- Add support to image formats (#121).
- Add HuggingFace sources (#106).

### Changed

- ragbits-core updated to version v0.2.0

## 0.1.0 (2024-10-08)

### Added

- Initial release of the package.
- Introduce core modules: documents, ingestion and retrival.
- Unstructured integration.
