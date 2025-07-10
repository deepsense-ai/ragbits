# CHANGELOG

## Unreleased

## 1.1.0 (2025-07-09)

### Changed

- ragbits-core updated to version v1.1.0

- Update qa data loader docstring (#565)
- Fix deadlock on qa metrics compute (#609)
- Upgrade distilabel version to 1.5.0 (#682)

## 1.0.0 (2025-06-04)

### Changed

- ragbits-core updated to version v1.0.0

## 0.20.1 (2025-06-04)

### Changed

- ragbits-core updated to version v0.20.1

## 0.20.0 (2025-06-03)

### Changed

- ragbits-core updated to version v0.20.0

## 0.19.1 (2025-05-27)

### Changed

- ragbits-core updated to version v0.19.1

## 0.19.0 (2025-05-27)

### Changed

- ragbits-core updated to version v0.19.0

- Add evals for question answering (#577)
- Add support for slicing dataset (#576)
- Separate load and map ops in data loaders (#576)

## 0.18.0 (2025-05-22)

### Changed

- ragbits-core updated to version v0.18.0

- Add support for custom column names in evaluation dataset (#566)
- Add support for reference document ids and page numbers in evaluation dataset (#566)
- BREAKING CHANGE: Adjust eval pipline interface to batch processing (#555)
- Rename DocumentMeta create_text_document_from_literal to from_literal (#561)
- Adjust typing for DocumentSearch (#554)

## 0.17.1 (2025-05-09)

### Changed

- ragbits-core updated to version v0.17.1

## 0.17.0 (2025-05-06)

### Changed

- ragbits-core updated to version v0.17.0

- Add tests for ragbits-evaluate package (#390)
- Integrate sources with dataloaders (#529)

## 0.16.0 (2025-04-29)

### Changed

- ragbits-core updated to version v0.16.0

## 0.15.0 (2025-04-28)

### Changed

- ragbits-core updated to version v0.15.0

## 0.14.0 (2025-04-22)

### Changed

- ragbits-core updated to version v0.14.0

- move sources from ragbits-document-search to ragbits-core (#496)

## 0.13.0 (2025-04-02)

### Changed

- ragbits-core updated to version v0.13.0

## 0.12.0 (2025-03-25)

### Changed

- ragbits-core updated to version v0.12.0

## 0.11.0 (2025-03-25)

### Changed

- ragbits-core updated to version v0.11.0

## 0.10.2 (2025-03-21)

### Changed

- ragbits-core updated to version v0.10.2

## 0.10.1 (2025-03-19)

### Changed

- ragbits-core updated to version v0.10.1

## 0.10.0 (2025-03-17)
### Changed

- ragbits-core updated to version v0.10.0

- Compability with the new Vector Store interface from ragbits-core (#288)
- chore: fix typo in README.
- fix typos in doc strings

## 0.9.0 (2025-02-25)

### Changed

- ragbits-core updated to version v0.9.0
- Add cli for document search evaluation added (#356)
- Add local data loader (#334).

## 0.8.0 (2025-01-29)

### Changed

- ragbits-core updated to version v0.8.0

## 0.7.0 (2025-01-21)

### Added

- Simplified interface to document-search evaluation (#258).

### Changed

- ragbits-core updated to version v0.7.0

## 0.6.0 (2024-12-27)

### Changed

- ragbits-core updated to version v0.6.0

## 0.5.1 (2024-12-09)

### Changed

- ragbits-core updated to version v0.5.1
- document search evaluation now returns all Element types, rather than only TextElements (#241).

## 0.5.0 (2024-12-05)

### Changed

- ragbits-core updated to version v0.5.0

## 0.4.0 (2024-11-27)

### Added

- Introduced optimization with optuna (#177).
- Add synthetic data generation pipeline (#165).

### Changed

- ragbits-core updated to version v0.4.0

## 0.3.0 (2024-11-06)

### Changed

- ragbits-core updated to version v0.3.0

## 0.2.0 (2024-10-23)

- Initial release of the package.
- Evaluation pipeline framework with capability to define evaluators & metrics.
- Evaluation pipeline for `ragbits-document-search`.

### Changed

- ragbits-core updated to version v0.2.0
