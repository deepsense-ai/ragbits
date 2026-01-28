# CHANGELOG

## Unreleased
- Decoupling of components from ragbits specific logic. Introduction of slot based plugin architecture. Minimal history store implementation (#917)
- Add timezone field to ChatContext, automatically populated from browser (#916)
- Fix PostgreSQL conversation persistence by ensuring session flush after creating new conversation in SQL storage (#903)
- Add file upload ingestion support with `upload_handler` in `ChatInterface` and `/api/upload` endpoint in `RagbitsAPI`.
- Change auth backend from jwt to http-only cookie based authentication, add support for OAuth2 authentication (#867)
- Add Google OAuth2 provider and refactor providers to use `OAuth2Providers` namespace (e.g., `OAuth2Providers.GOOGLE`) (#915)
- Make `SummaryGenerator` optional in `ChatInterface` by providing a default Heuristic implementation.
- Refactor ragbits-client types to remove excessive use of any (#881)
- Split params into path params, query params in API client (#871)
- Fix bug causing conversation not to be selected when navigating to it from url(#872)
- CI/CD for nightly npm builds, update ragbits-api-client-react deps to install latest version of the @ragbits/api-client (#873)
- CI/CD for nightlty builds improvements (#874)
- Add automatic topic extraction to be used as conversation title with ability to edit in the client side (#840)
- Add todo list component to the UI, add support for todo events in API (#827)
- Add support for confirmation requests in chat (#853) (#914)
- customizable HeroUI theme (#841)
- Add error response type to the chat interface with ability to display error messages to the user (#878)

### Added

- Make `SummaryGenerator` optional in `ChatInterface` by providing a default no-op implementation.
- Add automatic topic extraction to be used as conversation title with ability to edit in the client side (#840)
- Add todo list component to the UI, add support for todo events in API (#827)
- Add custom response type to the chat interface with full type safety and validation (#849)
  - New class-based response system: `TextResponse`, `ReferenceResponse`, `StateUpdateResponse`, etc.
  - Support for custom response types by extending `ResponseContent` and `ChatResponse`
  - Full Pydantic validation for all response content
- customizable HeroUI theme (#841)

### Deprecated

- **BACKWARD COMPATIBILITY MAINTAINED**: The following APIs are deprecated and will be removed in version 2.0.0:
  - `ChatResponseType` enum - Use `isinstance()` checks with specific response classes instead
  - `ChatResponse.type` property - Use `isinstance()` checks instead
  - `ChatResponse.as_text()` method - Use `isinstance(response, TextResponse)` instead
  - `ChatResponse.as_reference()` method - Use `isinstance(response, ReferenceResponse)` instead
  - `ChatResponse.as_state_update()` method - Use `isinstance(response, StateUpdateResponse)` instead
  - `ChatResponse.as_conversation_id()` method - Use `isinstance(response, ConversationIdResponse)` instead

All deprecated APIs emit `DeprecationWarning` when used and remain fully functional for backward compatibility.

**Migration Example:**

```python
# Old (deprecated but still works):
if response.type == ChatResponseType.TEXT:
    print(response.as_text())

# New (recommended):
if isinstance(response, TextResponse):
    print(response.content.text)
```

## 1.3.0 (2025-09-11)

### Changed

- ragbits-core updated to version v1.3.0

- fix: replace authenticated_user state tracking with direct user field in ChatContext
- Refactor chat handlers in the UI to use registry (#805)
- Add auth token storage and automatic logout on 401 (#802)
- Improve user settings storage when history is disabled (#799)
- Remove redundant test for `/api/config` endpoint (#795)
- Fix bug causing infinite initialization screen (#793)
- Fix bug that caused messages to be sent when changing chat settings; simplify and harden history logic (#791)
- Add `clear_message` event type allowing to reset whole message (#789)
- Add usage component to UI with backend support (#786)
- Add authentication handling in the UI (#763)
- Add backend authentication (#761)

- Autogenerate typescript types based on backend typing (#727)
- Add ability to customize favicon and page title (#766)

- Autogenerate typescript types based on backend typing (#727)
- Add ability to customize favicon and page title (#766)

## 1.2.2 (2025-08-08)

### Changed

- ragbits-core updated to version v1.2.2

## 1.2.1 (2025-08-04)

### Changed

- ragbits-core updated to version v1.2.1
- Fix routing error causing chat to not be displayed with disabled history (#764)

## 1.2.0 (2025-08-01)

### Changed

- ragbits-core updated to version v1.2.0
- Update TailwindCSS, React, Vite, tailwind config (#742)
- Add images support in chat message, images gallery (#731)
- Add persistent user settings (#719)
- Send chat options under `user_settings` key (#721)
- Add feedback indicator to messages, allow `extensions` in chat messages (#722)
- Add unit tests for UI's core components (#717)
- Add share functionality with informative modal (#726)
- Add persisent chat history to the default UI using IndexedDB (#732)
- Redesign history UI, allowed enabling of client side history using config (#744)
- Allow parallel conversations in the UI (#749)
- Add missing typography plugin for TailwindCSS (#750)
- Add client routing with ability for plugins to define custom routes (#754)

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
