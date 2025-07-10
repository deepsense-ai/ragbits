# CHANGELOG

## Unreleased

## 1.1.0 (2025-07-09)

### Changed

- ragbits-core updated to version v1.1.0

- Add configurable user setting in Ragbits UI (#692)
- Live updates support for Python api client(#683)
- Synchronous and asynchronous Python api client (#647)
- Live updates support markdown (#684)
- Added custom styling for multiline and inline-code (#668)
- Changed toggling darkmode for tailwind class selector (#668)
- Loading indicator, delayed message buttons, integrated abort controller (#641)
- Added Eslint, Prettier & CI/CD for Ragbits API Clients (#604)
- Excluded API connection logic to 2 modules: ragbits-api-client and ragbits-api-client-react which implements hooks for ragbits-api-client (#582)
- CI/CD changes for new directory structure (#582)
- Move form definitions to JSONSchema (#616)
- Allow UI cutomization using config endpoint (#643)
- Add support for live updates and followup messages (#654)
- Fix invalid context structure in requests from FE (#663)
- Arrow Up and Arrow Down now cycle through sent messages in a terminal-like style (#667)
- Fix followup messages not sending (#680)
- Improve typing of TypeScript libraries (#681)
- New metrics in for RagbitsAPI (#615)
- Add debug panel with debug_mode field in config (#689)
- Restore relative URL handling for UI build (#699)
- Add integration tests for UI (#697)
- Use external store instead of context for history (#706)

## 1.0.0 (2025-06-04)

### Changed

- ragbits-core updated to version v1.0.0

## 0.20.1 (2025-06-04)

### Changed

- ragbits-core updated to version v0.20.1

## 0.20.0 (2025-06-03)

### Changed

- ragbits-core updated to version v0.20.0

- remove HeroUI Pro components (#557)
- refactor UI components to allow modifications (#579)
- Add setup method to ChatInterface (#586)
- Rebuild UI with new dependencies (#589)

## 0.19.1 (2025-05-27)

### Changed

- ragbits-core updated to version v0.19.1

- fix: dont import all persistence strategies in base file (#584)

## 0.19.0 (2025-05-27)

### Changed

- ragbits-core updated to version v0.19.0

- Add persistance component to save chat interactions from ragbits-chat (#556)
- Add conversation_id parameter to chat interface context (#556)
- Add uvicorn to dependencies (#578)
- Remove HeroUI Pro components (#557)

## 0.18.0 (2025-05-22)

### Changed

- ragbits-core updated to version v0.18.0

- updated ui build (#553)
- api integration improvements + history context changes (#552)
- feedback form integration (#540)

## 0.17.1 (2025-05-09)

### Changed

- ragbits-core updated to version v0.17.1

## 0.17.0 (2025-05-06)

### Changed

- ragbits-core updated to version v0.17.0

## 0.16.0 (2025-04-29)

### Changed

- ragbits-core updated to version v0.16.0

## 0.15.0 (2025-04-28)

### Changed

- ragbits-core updated to version v0.15.0

### Added

- Added support for state updates in chat interfaces with automatic signature generation (#537).

## 0.14.0 (2025-04-22)

### Changed

- ragbits-core updated to version v0.14.0

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

## 0.9.0 (2025-02-25)

### Changed

- ragbits-core updated to version v0.9.0
- Add support to persisting history of conversations using sqlalchemy (#354).

## 0.8.0 (2025-01-29)

### Changed

- ragbits-core updated to version v0.8.0

## 0.7.0 (2025-01-21)

### Changed

- ragbits-core updated to version v0.7.0

### Added

- Initial release of the package (#271).
- Added last message recontextualization (#271).
