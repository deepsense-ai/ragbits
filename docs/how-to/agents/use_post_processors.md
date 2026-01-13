# How-To: Use Post-Processors with Ragbits Agents

Ragbits Agents can be enhanced with post-processors to intercept, validate, log, filter, and modify their outputs. In this guide you will learn how to:

- Create custom post-processors (streaming and non-streaming)
- Attach post-processors to agents in run and streaming modes
- Use and configure the built-in Supervisor post-processor

## Post-Processors Overview

Ragbits provides two types of post-processors:

- **PostProcessor**: Processes the final output after generation, ideal for end-of-run processing.
- **StreamingPostProcessor**: Processes outputs as they are generated, suitable for real-time applications.

### Implementing a custom Post-Processor

To create a custom post-processor, inherit from the appropriate base class ([`PostProcessor`][ragbits.agents.post_processors.base.PostProcessor] or [`StreamingPostProcessor`][ragbits.agents.post_processors.base.StreamingPostProcessor]) and implement the required method.

#### Post-Processor Example

A non-streaming post-processor applies transformations after the entire content is generated.

```python
class TruncateProcessor(PostProcessor):
    def __init__(self, max_length: int = 50) -> None:
        self.max_length = max_length

    async def process(self, result, agent, options=None, context=None):
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

To use post-processors, pass them to the `Agent` constructor during initialization. If you use a non-streaming processor with `run_streaming`, set `allow_non_streaming=True`. This allows streaming processors to handle content piece by piece during generation, while non-streaming processors apply transformations after the entire output is generated.

```python
async def main() -> None:
    llm = LiteLLM("gpt-4.1-mini")
    agent = Agent(
        llm=llm,
        prompt="You are a helpful assistant.",
        post_processors=[
            UpperCaseStreamingProcessor(),
            TruncateProcessor(max_length=50),
        ],
    )
    stream_result = agent.run_streaming(
        "Tell me about the history of AI.",
        allow_non_streaming=True
    )
    async for chunk in stream_result:
        if isinstance(chunk, str):
            print(chunk, end="")
    print(f"\nFinal answer:\n{stream_result.content}")
```

Post-processors offer a flexible way to tailor agent outputs, whether filtering content in real-time or transforming final outputs.

## Built-in Post-Processors

### Supervisor

The [`SupervisorPostProcessor`][ragbits.agents.post_processors.supervisor.SupervisorPostProcessor] validates the agent’s final response against the executed tool calls and, if needed, triggers an automatic rerun with a correction prompt. It helps catch inconsistencies (e.g., when the response contradicts tool output) and guide the agent to refine its answer. The Supervisor is a non-streaming post-processor: it runs after generation has completed, validating the final output before optionally issuing a correction rerun.

Key capabilities:

- Validates the last assistant response using an LLM-powered validation prompt
- Optionally reruns the agent with a formatted correction prompt derived from validation feedback
- Supports preserving or pruning intermediate history
- Attaches validation metadata to the final `AgentResult`

#### Quick start

```python
from ragbits.agents import Agent
from ragbits.agents.post_processors import SupervisorPostProcessor
from ragbits.agents.post_processors.supervisor import HistoryStrategy
from ragbits.core.llms.litellm import LiteLLM

llm = LiteLLM("gpt-4o-mini", use_structured_output=True)
supervisor = SupervisorPostProcessor(
    llm=llm,
    max_retries=2,
    fail_on_exceed=False,
    history_strategy=HistoryStrategy.PRESERVE,  # Default HistoryStrategy is REMOVE
)

agent = Agent(
    llm=llm,
    prompt="You are a helpful assistant.",
    post_processors=[supervisor],
)

result = await agent.run("What is the weather in Tokyo?")
```

#### Configuration

- **llm**: LLM used for validation and formatting structured outputs
- **validation_prompt**: Optional custom prompt class describing the validation output schema
- **correction_prompt**: Optional format string used to create a correction message from validation output
- **max_retries**: How many times to attempt correction-driven reruns
- **fail_on_exceed**: If `True`, raises when retries are exhausted; otherwise returns last result with metadata
- **history_strategy**:
    - `PRESERVE`: keep all messages, including the correction user message and rerun assistant message
    - `REMOVE`: prune the invalid assistant message and the correction user message, keeping the final assistant response succinctly

#### Custom structured validation and correction

You can define a custom validation output model and prompt to shape the supervisor feedback and correction message:

```python
from pydantic import BaseModel
from ragbits.core.prompt.prompt import Prompt
from ragbits.agents.post_processors.supervisor import ValidationInput

class MyValidationOutput(BaseModel):
    is_valid: bool
    errors: list[str]
    fixes: list[str]
    confidence: float

class MyValidationPrompt(Prompt[ValidationInput, MyValidationOutput]):
    system_prompt = "You are an expert validator. Provide clear, actionable feedback."
    user_prompt = (
        "Chat History:\n"
        "{% for message in chat_history %}"
        "\n{{ message.role | title }}: {{ message.content }} (if None it means it's a tool call)"
        "{% endfor %}"
        "\n\nList all errors, possible fixes, and provide a confidence score (0.0-1.0) for your assessment.\n"
    )

correction_prompt = (
    "Previous answer had issues:\n"
    "Errors: {errors}\n"
    "Fixes: {fixes}\n"
    "Confidence: {confidence}\n"
    "Please answer again using the fixes."
)

supervisor = SupervisorPostProcessor(
    llm=llm,
    validation_prompt=MyValidationPrompt,
    correction_prompt=correction_prompt,
    max_retries=1,
    history_strategy=HistoryStrategy.PRESERVE,
)
```

The Supervisor appends validation records to `result.metadata` under the `post_processors.supervisor` key as a list of dicts; each entry corresponds to a validation step.
