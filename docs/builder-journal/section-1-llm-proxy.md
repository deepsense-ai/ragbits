# Section 1: LLM Proxy — Streaming Chat API

In this section, you'll build a working chat application with an API that proxies requests to any LLM provider. This establishes the foundational pattern that all subsequent sections build upon, showing how Ragbits eliminates boilerplate so you can focus on business logic.

**What you get at the end:**

- FastAPI-powered REST endpoint at `/chat` accepting messages and returning streamed responses
- Built-in web UI served at root (`/`) with no frontend code required
- Provider-agnostic LLM access via LiteLLM (OpenAI, Anthropic, Azure, Bedrock, Ollama, 100+ providers)
- Streaming token delivery with Server-Sent Events (SSE) for real-time UX
- Typed response generation using `create_text_response()` for consistent output formatting

## Installation

Install Ragbits:

```bash
pip install ragbits
```

## Configuration

Set your LLM provider credentials. For OpenAI:

```bash
export OPENAI_API_KEY="your-api-key"
```

Ragbits uses [LiteLLM](https://docs.litellm.ai/docs/providers) under the hood, so you can use any of 100+ supported providers by setting the appropriate environment variables.

!!! tip "Other Providers"
    For Anthropic: `export ANTHROPIC_API_KEY="your-key"`

    For Azure OpenAI: `export AZURE_API_KEY="your-key"` and `export AZURE_API_BASE="your-endpoint"`

    For local models with Ollama: No API key needed, just have Ollama running.

## The Complete Application

Here's the entire application in about 30 lines of code:

[View full source on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py)

```python title="src/ragbits_example/main.py" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py"
```

Let's break down each component.

## Understanding the Components

### ChatInterface Contract

The `ChatInterface` abstract class enforces a clean separation between framework and implementation.

[View on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L23-L24)

```python linenums="23"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:23:24"
```

You implement the `chat()` method as an async generator, and Ragbits handles everything else: the REST API, streaming, CORS, and the web UI. This is the contract you'll use throughout the Builder Journal, adding capabilities without changing the core pattern.

### LiteLLM Integration

[View on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L26-L28)

```python linenums="26"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:26:28"
```

`LiteLLM` provides a unified interface across 100+ LLM providers. Switch models by changing the `model_name` parameter with no other code changes required:

| Provider | Model Name |
|----------|------------|
| OpenAI | `gpt-4o-mini`, `gpt-4o`, `o1` |
| Anthropic | `claude-sonnet-4-20250514`, `claude-3-5-haiku-20241022` |
| Azure | `azure/gpt-4o` |
| Ollama | `ollama/llama3.2` |
| Bedrock | `bedrock/anthropic.claude-3-sonnet` |

The library handles prompt formatting differences between providers, token counting, cost tracking hooks, and automatic retries on transient failures.

### The chat() Method

[View on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L30-L35)

```python linenums="30"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:30:35"
```

This is where your business logic lives. The method receives:

- **message**: The current user message
- **history**: Previous messages in OpenAI-compatible format (`ChatFormat`)
- **context**: Additional context including user info, settings, and state

It yields `ChatResponse` objects, one for each chunk of streamed content.

### Conversation History

[View on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L47-L50)

```python linenums="47"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:47:50"
```

The `history` parameter uses `ChatFormat`, which is OpenAI's message format:

```python
[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there! How can I help?"},
]
```

By appending the current message to history, you maintain full conversation context. Ragbits handles storing and passing this history between requests.

### Streaming Responses

[View on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L47-L50)

```python linenums="47"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:47:50"
```

The `generate_streaming()` method returns an async generator that yields text chunks as they arrive from the LLM. By using `yield` in an async generator, you enable real-time token delivery to the client.

The `create_text_response()` helper ensures your output conforms to the expected schema. Ragbits automatically converts these to Server-Sent Events (SSE) that the built-in UI handles.

## Running the Application

You have two options for running your chat app:

=== "CLI (Recommended)"

    ```bash
    ragbits api run ragbits_example.main:SimpleStreamingChat
    ```

    The format is `module.path:ClassName`. This is the recommended approach for development and production.

=== "Programmatic"

    ```bash
    python -m ragbits_example.main
    ```

    This uses the `if __name__ == "__main__"` block ([view on GitHub](https://github.com/deepsense-ai/ragbits-example/blob/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py#L53-L55)):

    ```python linenums="53"
   --8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/fc0bd1122f6c71eca9acf357f4b7c0f76727d71c/src/ragbits_example/main.py:53:55"
    ```

Both methods start a FastAPI server on `http://127.0.0.1:8000` with:

- **Web UI** at `/` for the chat interface
- **API endpoint** at `/chat` for programmatic access
- **Health check** at `/health` for deployment monitoring

### Server Options

Customize the server with CLI flags:

```bash
# Custom host and port
ragbits api run ragbits_example.main:SimpleStreamingChat --host 0.0.0.0 --port 9000

# Enable auto-reload for development
ragbits api run ragbits_example.main:SimpleStreamingChat --reload

# Enable debug mode
ragbits api run ragbits_example.main:SimpleStreamingChat --debug

# Enable CORS for frontend development
ragbits api run ragbits_example.main:SimpleStreamingChat --cors-origin http://localhost:3000
```

Or programmatically:

```python
api = RagbitsAPI(SimpleStreamingChat)
api.run(host="0.0.0.0", port=9000)
```

## Try It Out

1. Start the server:
   ```bash
   ragbits api run ragbits_example.main:SimpleStreamingChat
   ```

2. Open `http://127.0.0.1:8000` in your browser

3. Type a message and watch tokens stream in real-time

4. Send multiple messages and see conversation history maintained automatically

## Milestone Checklist

- [x] Ragbits installed, at least one LLM provider key configured
- [x] ChatInterface subclass created with streaming `chat()` implementation
- [x] Server running via CLI or code
- [x] Web UI accessible and functional
- [x] Multi-turn conversation works (history passed to LLM)
- [x] Response streams token-by-token in the UI

## What's Next

You now have a working chat application with streaming responses and a web UI, all in about 30 lines of code. In the next section, you'll add structured output to get type-safe, predictable responses from your LLM.

## Reference

| Component | Package | Purpose |
|-----------|---------|---------|
| `LiteLLM` | ragbits-core | Unified interface to 100+ LLM providers with automatic retries and fallbacks |
| `ChatInterface` | ragbits-chat | Abstract base class defining the `chat()` contract and response helpers |
| `RagbitsAPI` | ragbits-chat | FastAPI application factory with built-in UI serving and CORS handling |
| `ChatFormat` | ragbits-core | OpenAI-compatible message format for conversation history |
| `ChatResponse` | ragbits-chat | Typed response envelope for text, references, tool calls, and state updates |
