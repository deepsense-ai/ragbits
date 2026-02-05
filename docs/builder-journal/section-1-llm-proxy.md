# Section 1: LLM Proxy — Streaming Chat API

In this tutorial, you'll build a streaming chat application from scratch. We'll start with the simplest possible implementation and progressively add capabilities until we have a fully functional chat app with LLM integration and conversation history.

By the end, you'll understand how Ragbits handles the infrastructure so you can focus on your application logic.

## What You'll Build

A chat application that:

- Streams responses from any LLM provider in real-time
- Maintains conversation history across messages
- Provides a web UI out of the box
- Exposes a REST API for programmatic access

## Prerequisites

Before starting, make sure you have:

- Python 3.10 or higher installed
- An OpenAI API key (or another LLM provider key)

Install Ragbits:

=== "pip"

    ```bash
    pip install ragbits
    ```

=== "uv"

    ```bash
    uv add ragbits
    ```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

!!! tip "Other Providers"
    Ragbits uses [LiteLLM](https://docs.litellm.ai/docs/providers) under the hood, supporting 100+ providers:

    - Anthropic: `export ANTHROPIC_API_KEY="your-key"`
    - Azure OpenAI: `export AZURE_API_KEY="your-key"` and `export AZURE_API_BASE="your-endpoint"`
    - Ollama (local): No API key needed, just have Ollama running

## Step 1: Create a Minimal Chat Interface

Create a new file called `main.py` with the following code:

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/944f1dc/src/ragbits_example/main.py:10:28"
```

This is the core contract in Ragbits. The `ChatInterface` class requires you to implement one method: `chat()`. This method:

- Receives the user's `message`
- Receives the conversation `history` (we'll use this later)
- Receives additional `context` (user info, settings, etc.)
- Yields `ChatResponse` objects

The `create_text_response()` helper creates a properly formatted response. Since `chat()` is an async generator (note the `yield`), Ragbits can stream responses to the client as they're generated.

### Launch the Application

To run your chat interface, wrap it with `RagbitsAPI`. Add this to the bottom of your file:

```python
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/944f1dc/src/ragbits_example/main.py:31:33"
```

Run the application:

```bash
python main.py
```

Open http://127.0.0.1:8000 in your browser. You'll see a chat interface. Type a message and you'll get back "Hello! You said: [your message]".

This works, but it's not very useful yet. Let's add an actual LLM.

## Step 2: Add an LLM

Ragbits uses `LiteLLM` to provide a unified interface to 100+ LLM providers. Add the import and an `__init__` method to your class:

```python hl_lines="6 12-14"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/b69d2a3/src/ragbits_example/main.py:10:33"
```

The `model_name` parameter accepts any model supported by LiteLLM:

| Provider | Model Name |
|----------|------------|
| OpenAI | `gpt-4o-mini`, `gpt-4o`, `o1` |
| Anthropic | `claude-sonnet-4-20250514`, `claude-3-5-haiku-20241022` |
| Azure | `azure/gpt-4o` |
| Ollama | `ollama/llama3.2` |

The LLM is ready, but we're not using it yet. Let's connect it to our chat method.

## Step 3: Connect the LLM to Chat

Now let's make the LLM actually respond to messages. Update the `chat()` method:

```python hl_lines="7-10"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/93b8999/src/ragbits_example/main.py:26:37"
```

Here's what changed:

1. We create a `conversation` list with the user's message in OpenAI's chat format
2. We call `generate_streaming()` which returns an async generator
3. We iterate over the stream, yielding each chunk as it arrives

Run the app again and try it. You'll see the LLM's response stream in real-time, token by token.

But there's a problem: the LLM doesn't remember previous messages. Each message is treated as a new conversation. Let's fix that.

## Step 4: Add Conversation History

The `history` parameter contains all previous messages in the conversation. Update the `chat()` method to include history:

```python hl_lines="18"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/ade4e2b/src/ragbits_example/main.py:30:50"
```

The key change is spreading the `history` list before the current message:

```python
[*history, {"role": "user", "content": message}]
```

The `history` parameter uses the OpenAI chat format:

```python
[
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there! How can I help?"},
    {"role": "user", "content": "What's the weather like?"},
    # ... and so on
]
```

Ragbits automatically manages this history for you. Each time the user sends a message, the previous messages are passed to your `chat()` method.

Run the app and have a multi-turn conversation. The LLM now remembers what you discussed earlier.

## Running with the CLI

So far we've been running the app with `python main.py`. Ragbits also provides a CLI that offers more options:

```bash
ragbits api run main:SimpleStreamingChat
```

The format is `module.path:ClassName`. The CLI supports additional flags:

```bash
# Custom host and port
ragbits api run main:SimpleStreamingChat --host 0.0.0.0 --port 9000

# Auto-reload when code changes (useful for development)
ragbits api run main:SimpleStreamingChat --reload

# Enable debug mode
ragbits api run main:SimpleStreamingChat --debug
```

## The Complete Application

Here's the final code that includes everything we built:

[View full source on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/ade4e2b/src/ragbits_example/main.py)

```python title="main.py" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/ade4e2b/src/ragbits_example/main.py"
```

## What You've Learned

In this tutorial, you:

1. Created a minimal `ChatInterface` implementation
2. Launched it with `RagbitsAPI` to get a web UI and REST API
3. Integrated an LLM using `LiteLLM`
4. Added streaming responses for real-time output
5. Enabled conversation history for multi-turn chats

The key insight: Ragbits handles the infrastructure (API server, streaming, UI, history management) so you can focus on your application logic. Your `chat()` method is where your business logic lives.

## What's Next

You now have a working chat application with streaming responses and conversation history. In the next section, you'll add structured output to get type-safe, predictable responses from your LLM.

## Reference

| Component | Package | Purpose |
|-----------|---------|---------|
| `ChatInterface` | ragbits-chat | Abstract base class defining the `chat()` contract |
| `RagbitsAPI` | ragbits-chat | FastAPI application with built-in UI and streaming |
| `LiteLLM` | ragbits-core | Unified interface to 100+ LLM providers |
| `ChatFormat` | ragbits-core | OpenAI-compatible message format |
| `ChatResponse` | ragbits-chat | Response envelope for streaming content |
