# How-To: Use Post-Processors with Ragbits Agents

Ragbits Agents can be enhanced with post-processors to intercept, log, filter, and modify their outputs. This guide explains how to implement and use post-processors to customize agent responses.

## Post-Processors Overview

Ragbits provides two types of post-processors:

- **PostProcessor**: Processes the final output after generation, ideal for batch processing.
- **StreamingPostProcessor**: Processes outputs as they are generated, suitable for real-time applications.

### Implementing a custom Post-Processor

To create a custom post-processor, inherit from the appropriate base class ([`PostProcessor`][ragbits.agents.post_processors.base.PostProcessor] or [`StreamingPostProcessor`][ragbits.agents.post_processors.base.StreamingPostProcessor]) and implement the required method.

#### Post-Processor Example

A non-streaming post-processor applies transformations after the entire content is generated.

```python
class TruncateProcessor(PostProcessor):
    def __init__(self, max_length: int = 50) -> None:
        self.max_length = max_length

    async def process(self, result, agent):
        content = result.content
        if len(content) > self.max_length:
            content = content[:self.max_length] + "... [TRUNCATED]"
        result.content = content
        return result
```

#### Streaming Post-Processor Example

A streaming post-processor can manipulate all information returned during generation, including text, tool calls, etc.

```python
class UpperCaseStreamingProcessor(StreamingPostProcessor):
    async def process_streaming(self, chunk, agent):
        if isinstance(chunk, str):
            return chunk.upper()
        return chunk
```

## Using Post-Processors

To use post-processors, pass them to the `run` or `run_streaming` methods of the `Agent` class. If you pass a non-streaming processor to `run_streaming`, set `allow_non_streaming=True`. This allows streaming processors to handle content piece by piece during generation, while non-streaming processors apply transformations after the entire output is generated.

```python
async def main() -> None:
    llm = LiteLLM("gpt-4.1-mini")
    agent = Agent(llm=llm, prompt="You are a helpful assistant.")
    post_processors = [
        UpperCaseStreamingProcessor(),
        TruncateProcessor(max_length=50),
    ]
    stream_result = agent.run_streaming("Tell me about the history of AI.", post_processors=post_processors, allow_non_streaming=True)
    async for chunk in stream_result:
        if isinstance(chunk, str):
            print(chunk, end="")
    print(f"\nFinal answer:\n{stream_result.content}")
```

Post-processors offer a flexible way to tailor agent outputs, whether filtering content in real-time or transforming final outputs.
