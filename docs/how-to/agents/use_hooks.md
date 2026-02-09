# How-To: Use hooks to customize agent behavior

Ragbits provides a hook system that lets you intercept and modify agent behavior at key points in the execution lifecycle. Hooks allow you to validate inputs, modify arguments, mask outputs, enforce guardrails, require user confirmation, and more — all without changing the agent or tool code itself.

The hook system supports four event types:

- **`PRE_TOOL`** — triggered before a tool is invoked
- **`POST_TOOL`** — triggered after a tool completes
- **`PRE_RUN`** — triggered before the agent run starts
- **`POST_RUN`** — triggered after the agent run completes

Hooks are executed in priority order (lower numbers first) and support **chaining** — each hook receives the output of the previous one, enabling composable pipelines of transformations.

## How to create and register a hook

A hook is an instance of [`Hook`][ragbits.agents.hooks.Hook] that binds an async callback to a lifecycle event. You pass hooks directly to the [`Agent`][ragbits.agents.Agent] constructor:

```python
from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook, PreToolInput, PreToolOutput
from ragbits.core.llms import LiteLLM


async def my_hook(input_data: PreToolInput) -> PreToolOutput:
    """A simple pre-tool hook that passes all calls through."""
    return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")


agent = Agent(
    llm=LiteLLM("gpt-4o-mini"),
    tools=[...],
    hooks=[
        Hook(
            event_type=EventType.PRE_TOOL,
            callback=my_hook,
            tool_names=["my_tool"],  # None = apply to all tools
            priority=10,             # lower runs first (default: 100)
        ),
    ],
)
```

The `Hook` constructor accepts:

- **`event_type`** — one of `EventType.PRE_TOOL`, `POST_TOOL`, `PRE_RUN`, or `POST_RUN`
- **`callback`** — an async function matching the corresponding input/output types
- **`tool_names`** — optional list of tool names this hook applies to. If `None`, the hook runs for every tool. This parameter is only relevant for `PRE_TOOL` and `POST_TOOL` hooks.
- **`priority`** — execution order; lower numbers execute first (default: `100`)

## How to validate and modify tool inputs with pre-tool hooks

Pre-tool hooks receive a [`PreToolInput`][ragbits.agents.hooks.PreToolInput] and return a [`PreToolOutput`][ragbits.agents.hooks.PreToolOutput]. The output includes a **decision** field that controls whether the tool executes:

- `"pass"` — allow the tool to run (optionally with modified arguments)
- `"deny"` — block the tool from running (requires a `reason`)
- `"ask"` — request user confirmation before proceeding (requires a `reason`)

### Validate inputs

This hook validates that an email argument has a correct format before allowing the `send_notification` tool to execute:

```python
--8<-- "examples/agents/hooks/validation_and_sanitization.py:37:54"
```

If validation fails, the hook returns `decision="deny"` which immediately stops tool execution and returns the reason to the LLM.

### Modify arguments

This hook rewrites email domains to an approved list, demonstrating how pre-tool hooks can modify tool arguments:

```python
--8<-- "examples/agents/hooks/validation_and_sanitization.py:57:87"
```

The modified `arguments` dict is passed to the next hook in the chain (or to the tool itself if this is the last hook).

### Chain multiple pre-tool hooks

When multiple pre-tool hooks are registered, they execute in priority order and each hook sees the arguments modified by the previous one. If any hook returns `"deny"`, execution stops immediately:

```python
--8<-- "examples/agents/hooks/validation_and_sanitization.py:139:152"
```

In this example, `validate_email` (priority 10) runs first. If it passes, `sanitize_email_domain` (priority 20) runs next and may modify the email argument before the tool executes.

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/hooks/validation_and_sanitization.py).

## How to modify tool outputs with post-tool hooks

Post-tool hooks receive a [`PostToolInput`][ragbits.agents.hooks.PostToolInput] (containing the original `tool_call` and the `tool_return`) and return a [`PostToolOutput`][ragbits.agents.hooks.PostToolOutput] with the (possibly modified) tool output.

### Mask sensitive data

This hook replaces sensitive fields in search results before they reach the LLM:

```python
--8<-- "examples/agents/hooks/validation_and_sanitization.py:90:112"
```

### Log tool outputs

This hook logs the output of specific agent tools without modifying the result:

```python
--8<-- "examples/agents/hooks/agent_output_logging.py:15:23"
```

To apply it only to specific tools, use the `tool_names` parameter:

```python
--8<-- "examples/agents/hooks/agent_output_logging.py:45:50"
```

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/hooks/agent_output_logging.py).

## How to validate agent input with pre-run hooks

Pre-run hooks execute before the agent starts processing. They receive a [`PreRunInput`][ragbits.agents.hooks.PreRunInput] (containing the user input, options, and context) and return a [`PreRunOutput`][ragbits.agents.hooks.PreRunOutput].

A common use case is integrating guardrails to block unsafe or policy-violating inputs:

```python
--8<-- "examples/agents/hooks/guardrails_integration.py:46:62"
```

To block the agent from processing the input, the hook returns a `PreRunOutput` with a replacement message. This message becomes the agent's final output — no LLM call or tool execution happens.

Register it with the agent:

```python
--8<-- "examples/agents/hooks/guardrails_integration.py:71:75"
```

!!! tip
    Pre-run hooks also work with streaming via `agent.run_streaming()`. If a pre-run hook replaces the input, the replacement text is streamed back directly.

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/hooks/guardrails_integration.py).

## How to modify agent results with post-run hooks

Post-run hooks execute after the agent completes its run. They receive a [`PostRunInput`][ragbits.agents.hooks.PostRunInput] (containing the `AgentResult`, options, and context) and return a [`PostRunOutput`][ragbits.agents.hooks.PostRunOutput].

Use post-run hooks to transform, enrich, or log final results:

```python
from ragbits.agents.hooks import EventType, Hook, PostRunInput, PostRunOutput


async def enrich_result(input_data: PostRunInput) -> PostRunOutput:
    """Add metadata to the agent result."""
    result = input_data.result
    result.metadata["processed_by"] = "post_run_hook"
    return PostRunOutput(result=result)


hook = Hook(event_type=EventType.POST_RUN, callback=enrich_result)
```

## How to require user confirmation before tool execution

Ragbits includes a built-in [`create_confirmation_hook`][ragbits.agents.hooks.create_confirmation_hook] factory that creates a pre-tool hook requiring user approval before a tool runs:

```python
from ragbits.agents import Agent
from ragbits.agents.hooks import create_confirmation_hook
from ragbits.core.llms import LiteLLM


agent = Agent(
    llm=LiteLLM("gpt-4o-mini"),
    tools=[delete_file, send_email],
    hooks=[
        create_confirmation_hook(tool_names=["delete_file", "send_email"]),
    ],
)
```

When the agent attempts to call one of the specified tools, the hook returns a `ConfirmationRequest` containing:

- `confirmation_id` — a deterministic ID based on the hook, tool name, and arguments
- `tool_name` — the name of the tool being called
- `tool_description` — a description of why confirmation is needed
- `arguments` — the tool arguments

The agent yields the `ConfirmationRequest` and pauses. You can then resume the agent with the user's decision by including it in the `AgentRunContext.tool_confirmations` list.

## How hook chaining works

All hook types support **chaining**: hooks execute in priority order, and each hook receives the output of the previous one.

```
Hook A (priority=10) → modified data → Hook B (priority=20) → modified data → Hook C (priority=100)
```

For **pre-tool hooks**, the chained value is the `arguments` dict. For **post-tool hooks**, it is the `tool_return`. For **pre-run hooks**, it is the agent `input`. For **post-run hooks**, it is the `AgentResult`.

This makes it possible to compose independent hooks that each handle one concern (validation, sanitization, logging, etc.) into a clean pipeline.

!!! warning
    For pre-tool hooks, if any hook in the chain returns `"deny"`, execution stops immediately and subsequent hooks do not run. Design your hooks with this in mind — place critical validation hooks at lower priority numbers so they run first.
