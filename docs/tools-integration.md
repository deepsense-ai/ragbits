# Tools system in ragbits-chat

## What was done

A generic tool system was added to `ragbits-chat` that allows the LLM to call external APIs during a conversation. The first implementation is Google Calendar. The user sees an "Available Tools" panel in the sidebar, clicks "Connect", goes through Google OAuth and from that point the LLM can answer questions about their calendar.

---

## New files

### `packages/ragbits-chat/src/ragbits/chat/tools/base.py`

Abstract base class for all tools. Every tool must extend it.

```python
class ChatTool(ABC):
    tool_id: str          # function name visible to the LLM
    display_name: str     # label in the UI panel
    category: str         # group in the UI panel
    has_access: bool = True
    google_scope: str | None = None  # e.g. "calendar", "drive" - triggers the Connect button

    @abstractmethod
    def build(self, context: ChatContext) -> Tool:
        ...
```

`build(context)` is called on every request. This allows the tool to capture `session_id` in a closure so it knows whose token to fetch from the store.

### `packages/ragbits-chat/src/ragbits/chat/tools/token_store.py`

A singleton in process memory that stores OAuth tokens per user.

```
InMemoryOAuthTokenStore
{
  "session_abc" -> { "calendar" -> OAuthTokenData(access_token="ya29...") }
  "session_xyz" -> { "calendar" -> OAuthTokenData(access_token="ya29...") }
}
```

`api.py` writes a token after the OAuth callback. Tools read it via `get_token_store().get_access_token(session_id, scope_group)`.

**Limitations (PoC):** Tokens are stored only in process memory. A server restart loses all tokens and the user has to click "Connect" again. With multiple server instances behind a load balancer each instance has its own store which can cause errors. In production `InMemoryOAuthTokenStore` should be replaced with a Redis or database-backed implementation. The interface (`save`, `get_access_token`) stays the same, only the backend changes.

### `packages/ragbits-chat/src/ragbits/chat/tools/google_calendar.py`

Google Calendar tool implementation. The LLM can call `search_calendar_events(query, time_min, time_max, calendar_id)` which queries the Google Calendar API and returns a formatted list of events.

### `typescript/ui/src/plugins/ToolsPlugin/`

A new frontend plugin that registers the "Available Tools" panel in the `layout.sidebarBottom` slot. The panel fetches the tool list from `/api/config`, checks OAuth status from `/api/auth/google/status` and shows a "Connect" button for tools that require authorization.

---

## Modified files

### `packages/ragbits-chat/src/ragbits/chat/interface/_interface.py`

`ChatInterface` is the base class for all chat implementations in ragbits. Two things were added:

- `tools: list[ChatTool] = []` attribute so a developer can declare tools directly on their class without touching the framework
- `run_with_tools()` method so developers don't have to manually create an agent and handle streaming. It creates a ragbits agent with the registered tools, streams the response as `TextResponse` and automatically emits `LiveUpdateResponse` (a badge in the UI) when the LLM calls a tool

### `packages/ragbits-chat/src/ragbits/chat/interface/types.py`

The frontend needs to know which tools exist in order to render the panel. `ToolEntry` was added as a type that gets serialized to JSON in the `/api/config` response. It contains everything the UI needs: name, category, whether the tool has access and which Google scope is required so the UI knows whether to show the "Connect" button.

### `packages/ragbits-chat/src/ragbits/chat/api.py`

Standard Google OAuth (used for login) only allows scopes declared at application startup. To let the user grant calendar access after login without re-logging in, an "incremental OAuth" mechanism is needed - a separate OAuth flow for a specific scope only. The following was added:

- `_GOOGLE_SCOPE_GROUPS` dict that maps a short group name (`"calendar"`) to the full Google scope URL so tool code does not need to know these URLs
- `GET /api/auth/google/connect?scope=<group>` starts the incremental OAuth flow and redirects to Google requesting only that one scope
- `GET /api/auth/google/callback` receives the token from Google, saves it to `InMemoryOAuthTokenStore` tied to the user's `session_id` and returns a page with `window.close()` instead of a redirect so the popup closes automatically without opening a new tab
- `GET /api/auth/google/status` is polled by the frontend after the popup closes to find out which scopes were granted and update the UI (green dot instead of "Connect")
- `available_tools` in `/api/config` is fetched by the frontend on startup so it knows what to render in the panel

### `typescript/@ragbits/api-client/src/autogen.types.ts`

The TypeScript client generates types from OpenAPI. `ToolEntry` and `GoogleIncrementalOAuthConfig` were added to `ConfigResponse` so the frontend has typed API data instead of casting to `any`.

### `typescript/ui/src/core/types/slots.ts`

The ragbits UI uses a slot system where each plugin can inject its component into a defined layout location without modifying existing components. The `"layout.sidebarBottom"` slot was added so `ToolsPlugin` has a place to attach.

### `typescript/ui/src/plugins/ChatHistoryPlugin/components/ChatHistory.tsx`

The sidebar was rendered without a place for additional components at the bottom. `<Slot name="layout.sidebarBottom">` was added at the bottom of the sidebar so the tools panel and potentially other future plugins have a place to render.

### `typescript/ui/src/main.tsx` and `PluginActivator.tsx`

Plugins in the ragbits UI must be explicitly registered at application startup. `ToolsPlugin` was registered here.

### `examples/chat/authenticated_chat.py`

The file was already in the repo as an authentication example. It was extended (without removing existing code) with:

- `GoogleOAuthBackend` which overrides `generate_authorize_url()` to add `access_type=offline&prompt=consent`. Without `access_type=offline` Google does not issue a refresh token so after one hour the token expires with no way to renew it without logging in again. `prompt=consent` forces the consent screen even if the user already authorized the app previously which is needed for Google to issue a new refresh token.
- `MyChatWithTools` which is a minimal implementation showing how to use tools: `tools = [GoogleCalendarTool()]` and `run_with_tools()` in the `chat()` method
- `get_google_calendar_auth_backend()` which is a factory function required by the ragbits CLI (`--auth` argument)

---

## How the OAuth flow works

```
User clicks "Connect" in the panel
        |
Frontend opens popup: GET /api/auth/google/connect?scope=calendar
        |
Backend redirects to Google OAuth (accounts.google.com)
        |
User grants permissions
        |
Google redirects to GET /api/auth/google/callback?code=...
        |
Backend exchanges code for access_token (POST to Google)
Backend saves token: token_store.save(session_id, "calendar", token)
Backend returns HTML: <script>window.close();</script>
        |
Popup closes, frontend detects popup.closed
Frontend polls /api/auth/google/status -> green dot in the panel
        |
On the next user message:
run_with_tools() calls tool.build(context)
Tool fetches token: token_store.get_access_token(session_id, "calendar")
LLM calls search_calendar_events(...) -> Google Calendar API -> response
```

---

## How to add a new tool

### Case 1: Google API (Drive, BigQuery as a user, People)

Add the scope to `_GOOGLE_SCOPE_GROUPS` in `api.py`:
```python
"bigquery": ["https://www.googleapis.com/auth/bigquery.readonly"],
```

Create a tool class:
```python
class BigQueryUserTool(ChatTool):
    tool_id = "query_bigquery"
    display_name = "BigQuery"
    category = "Data Sources"
    google_scope = "bigquery"

    def build(self, context: ChatContext) -> Tool:
        session_id = context.session_id

        async def query_bigquery(sql: str) -> str:
            """Run a BigQuery SQL query."""
            token = get_token_store().get_access_token(session_id, "bigquery")
            if not token:
                return "BigQuery not connected. Click Connect in the Available Tools panel."
            # call BigQuery API with the token...

        return Tool.from_callable(query_bigquery)
```

Register in `ChatInterface`:
```python
class MyChat(ChatInterface):
    tools = [GoogleCalendarTool(), BigQueryUserTool()]
```

### Case 2: External API without OAuth (BigQuery Service Account, databases)

`google_scope = None` means no Connect button and the tool is active immediately.

```python
class BigQueryTool(ChatTool):
    tool_id = "query_bigquery"
    display_name = "BigQuery"
    category = "Data Sources"
    google_scope = None

    def build(self, context: ChatContext) -> Tool:
        async def query_bigquery(sql: str) -> str:
            """Run a BigQuery SQL query."""
            client = bigquery.Client()  # reads credentials from env
            # ...
        return Tool.from_callable(query_bigquery)
```

### Case 3: A different OAuth provider (Slack, Outlook, Microsoft)

This requires adding new endpoints for that provider in `api.py` (analogous to `/api/auth/google/*`) and extending the frontend to handle the new provider in `ToolsPanel`. This is a one-time effort per provider. After that every subsequent tool for that provider reuses the same endpoints.

---

## Running the example

```bash
export RAGBITS_BASE_URL=http://localhost:8000
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
python examples/chat/authenticated_chat.py
```

Prerequisites in Google Cloud Console:
1. Google Calendar API enabled
2. Scope `https://www.googleapis.com/auth/calendar.readonly` added to the OAuth consent screen
3. `http://localhost:8000/api/auth/google/callback` added as an authorized redirect URI
