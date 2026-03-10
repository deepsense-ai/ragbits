# Section 2: Application Configuration — Identity, Persistence & Customization

In this section, you'll transform the basic chat app from Section 1 into a fully configurable application. You'll add branding, persistent conversations, user settings, state tracking, feedback collection, authentication, follow-up suggestions, and file uploads — all through Ragbits' declarative configuration system.

By the end, you'll see how Ragbits uses class attributes and Pydantic models to turn configuration into working features without any boilerplate.

## What You'll Build

A chat application that:

- Displays custom branding with a header, welcome message, and starter questions
- Persists conversation history to disk so chats survive page reloads
- Lets users pick their preferred LLM model from a settings panel
- Tracks state across messages with signed state updates
- Collects like/dislike feedback with custom forms
- Requires user authentication with a login gate
- Suggests follow-up messages after each response
- Accepts file uploads and uses their content as LLM context

## Prerequisites

Before starting, make sure you have completed [Section 1: LLM Proxy](section-1-llm-proxy.md). You should have a working streaming chat application with LLM integration and conversation history.

## Step 1: Customize the Application UI

Ragbits lets you brand your chat interface by setting a `ui_customization` class attribute. Start by extracting your configuration into a separate file.

Create `config.py`:

```python title="config.py" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/941e5c7/src/ragbits_example/config.py"
```

The `UICustomization` object controls what users see when they first open the app — a branded header, a Markdown welcome message, clickable starter questions, and the browser tab title.

Now import and assign it in your chat class:

```python hl_lines="9 15"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/941e5c7/src/ragbits_example/main.py:14:28"
```

Setting `ui_customization` as a class attribute is all Ragbits needs. The framework reads it when building the UI and API responses. Run the app and you'll see your branded header, welcome message, and starter questions.

## Step 2: Persist Conversation History

By default, conversations are lost when the page reloads. Add a persistence import and two class attributes to fix that:

```python hl_lines="3 15 16"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fcebd10/src/ragbits_example/main.py:17:32"
```

`conversation_history = True` tells Ragbits to store and replay messages. `FileHistoryPersistence` saves them as JSONL files in the `./chat_history` directory. Refresh the page after sending a few messages — your conversation is still there.

## Step 3: Let Users Choose Their Model

Ragbits can render a settings panel from a Pydantic model. Add a default model constant and a settings form to `config.py`:

```python hl_lines="3 5 7 10"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d8efab4/src/ragbits_example/config.py:1:10"
```

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d8efab4/src/ragbits_example/config.py:30:41"
```

`UserSettingsForm` is a Pydantic model that Ragbits renders as a form in the UI. The `Literal` type creates a dropdown, and the `Field` description becomes the label. Wrapping it in `UserSettings` connects it to the framework.

Now wire it into your chat class and read the selected model at runtime:

```python hl_lines="1 8 14"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d8efab4/src/ragbits_example/main.py:23:36"
```

The import now includes `DEFAULT_MODEL` and `user_settings`. The `user_settings` class attribute tells Ragbits to show the settings panel. In `__init__`, the hardcoded model string is replaced with the constant.

Update the `chat()` method to respect the user's choice:

```python hl_lines="1 2 3 5"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d8efab4/src/ragbits_example/main.py:55:63"
```

The method reads the selected model from `context.user_settings` and creates a fresh `LiteLLM` instance. If no setting is saved yet, it falls back to the default.

## Step 4: Track State Across Messages

Sometimes you need to carry data between turns without storing it in conversation history. Ragbits provides HMAC-signed state updates for this. Add a message counter to the `chat()` method:

```python hl_lines="3 8"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d276ee3/src/ragbits_example/main.py:60:67"
```

`context.state` is a dictionary that persists across messages via signed cookies. After streaming the response, `create_state_update()` sends the updated state back to the client. The state is tamper-proof — Ragbits signs it with HMAC so the client can't modify it.

## Step 5: Collect User Feedback

Ragbits can add like/dislike buttons to every response and show custom feedback forms. Define the forms in `config.py`:

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/b170986/src/ragbits_example/config.py:44:74"
```

`LikeFeedbackForm` asks for a free-text reason. `DislikeFeedbackForm` uses a `Literal` dropdown for the issue type plus a details field. `FeedbackConfig` enables both buttons and connects them to the forms.

Wire the feedback into your chat class and implement the storage handler:

```python hl_lines="6 10"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/b170986/src/ragbits_example/main.py:33:42"
```

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/b170986/src/ragbits_example/main.py:78:94"
```

The `feedback_config` class attribute enables the UI buttons. `feedback_path` defines where to store the data. The `save_feedback()` method appends each feedback entry as a JSON line with a timestamp. Call `super().save_feedback()` first to let Ragbits handle any built-in processing.

## Step 6: Require Authentication

Ragbits supports pluggable authentication backends. Add a demo backend to `config.py`:

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d5f7e98/src/ragbits_example/config.py:79:97"
```

`ListAuthenticationBackend` is a simple backend that checks credentials against an in-memory list. `InMemorySessionStore` manages login sessions. In production, you'd swap these for a database-backed implementation.

Now use the authenticated user in your `chat()` method to greet them on the first message:

```python hl_lines="12 13 14"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d5f7e98/src/ragbits_example/main.py:54:67"
```

`context.user` contains the authenticated user's details. The greeting only fires when there's no history — meaning it's the first message in the conversation.

Pass the auth backend when creating the API:

```python hl_lines="2"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/d5f7e98/src/ragbits_example/main.py:102:104"
```

## Step 7: Suggest Follow-up Messages

After each response, you can suggest clickable follow-up messages to guide the conversation. Add a single yield after the state update:

```python hl_lines="6 7 8 9 10"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/b87eb9c/src/ragbits_example/main.py:78:87"
```

`create_followup_messages()` sends a list of suggestions that appear as clickable buttons below the response. The user can click one to send it as their next message, or ignore them and type their own.

## Step 8: Accept File Uploads

Ragbits supports file uploads through an `upload_handler` method. Uploaded files are parsed with Docling and injected as system context for the LLM.

First, add a dictionary to track uploaded files in `__init__`:

```python hl_lines="3"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/cb2ff6c/src/ragbits_example/main.py:50:52"
```

Update the `chat()` method to build a conversation that includes file content as a system message:

```python hl_lines="1 2 3 4 5 6 7 10"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/cb2ff6c/src/ragbits_example/main.py:79:88"
```

When files have been uploaded, their content is prepended as a system message. This gives the LLM full context about the uploaded documents without modifying the user's conversation history.

Finally, implement the `upload_handler` method:

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/cb2ff6c/src/ragbits_example/main.py:121:137"
```

The handler writes the uploaded file to a temporary location, uses `DoclingDocumentParser` to extract text from any supported format (PDF, DOCX, etc.), and stores the parsed text keyed by filename.

!!! tip "Install Docling"
    File upload parsing requires the `docling` extra. Install it with `pip install ragbits[docling]` or `uv add ragbits[docling]`.

## Running with the CLI

The CLI supports an `--auth` flag to enable authentication:

```bash
# Without authentication
ragbits api run ragbits_example.main:SimpleStreamingChat

# With authentication
ragbits api run ragbits_example.main:SimpleStreamingChat \
    --auth ragbits_example.config:get_auth_backend
```

The `--auth` flag takes a `module:function` reference that returns an authentication backend.

## The Complete Application

Here's the final code that includes everything we built:

[View full source on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/cb2ff6c/src/ragbits_example/)

```python title="config.py" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/cb2ff6c/src/ragbits_example/config.py"
```

```python title="main.py" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/cb2ff6c/src/ragbits_example/main.py"
```

## What You've Learned

In this section, you:

1. Extracted configuration into a dedicated `config.py` with `UICustomization`
2. Added file-based conversation persistence with `FileHistoryPersistence`
3. Built a settings form from a Pydantic model with `UserSettings`
4. Used signed state updates to carry data between turns
5. Added like/dislike feedback with custom Pydantic forms
6. Enabled authentication with `ListAuthenticationBackend`
7. Added clickable follow-up suggestions with `create_followup_messages()`
8. Implemented file uploads with Docling-powered document parsing

The key pattern: Ragbits uses class attributes and Pydantic models as a declarative configuration layer. You describe *what* you want (a settings form, feedback buttons, auth), and the framework handles the UI rendering, API endpoints, and state management.

## What's Next

You now have a fully configured chat application with branding, persistence, settings, feedback, auth, and file uploads. In the next section, you'll add retrieval-augmented generation (RAG) to ground your LLM's responses in your own documents.

## Reference

| Component | Package | Purpose |
|-----------|---------|---------|
| `UICustomization` | ragbits-chat | Branded header, welcome message, starter questions, page meta |
| `FileHistoryPersistence` | ragbits-chat | JSONL-based conversation persistence |
| `UserSettings` | ragbits-chat | Settings panel rendered from a Pydantic model |
| `FeedbackConfig` | ragbits-chat | Like/dislike buttons with custom feedback forms |
| `ListAuthenticationBackend` | ragbits-chat | Credential-based authentication with in-memory user list |
| `InMemorySessionStore` | ragbits-chat | Session management for authenticated users |
| `DoclingDocumentParser` | ragbits-document-search | Multi-format document parser for file uploads |
| `create_state_update()` | ragbits-chat | HMAC-signed state passed between turns |
| `create_followup_messages()` | ragbits-chat | Clickable follow-up suggestions |
