# How-To: Agent Simulation for Evaluation

Agent simulation allows you to evaluate your agents by having them interact with a simulated user in realistic conversation scenarios. This is particularly useful for testing agent behavior, tool usage, and task completion in a controlled environment.

## Overview

The agent simulation framework consists of several key components:

- **Simulated User**: An LLM-driven user that generates realistic messages based on tasks and conversation history
- **Checker System**: A pluggable framework for validating task completion using LLM evaluation, tool call verification, or state checks
- **Metric Collectors**: Track latency, token usage, and tool usage throughout the simulation
- **Conversation Logger**: Records all conversation turns, tool calls, and evaluation results
- **DeepEval Integration**: Optional evaluation of conversation quality using DeepEval metrics
- **Structured Results**: Programmatic access to simulation results via `SimulationResult`

## Creating Scenarios

Scenarios define the tasks your agent should complete. Each scenario contains a list of tasks that are completed sequentially.

Create a `scenarios.json` file:

```json
[
  {
    "name": "Hotel Booking Scenario",
    "tasks": [
      {
        "task": "find hotels in Warsaw",
        "checkers": [
          {"type": "llm", "expected_result": "{list of hotels in Warsaw}"},
          {"type": "tool_call", "tools": ["list_hotels"]}
        ],
        "checker_mode": "all"
      },
      {
        "task": "check availability for 3 nights from April 1, 2025",
        "checkers": [
          {"type": "llm", "expected_result": "{available rooms for specified dates}"},
          {"type": "tool_call", "tools": ["search_available_rooms"]}
        ],
        "checker_mode": "all"
      },
      {
        "task": "book a budget-friendly room",
        "checkers": [
          {"type": "llm", "expected_result": "{booking confirmation}"},
          {"type": "tool_call", "tools": ["create_reservation"]}
        ],
        "checker_mode": "all"
      }
    ]
  }
]
```

Each task has:

- **task**: Description of what the user wants to accomplish
- **checkers**: List of checker configurations that validate task completion (see [Checker System](#checker-system))
- **checker_mode**: How to combine multiple checkers — `"all"` (all must pass) or `"any"` (at least one must pass). Defaults to `"all"`.

Scenarios also support optional file-level grouping:

```json
{
  "group": "Hotel Booking",
  "scenarios": [
    {"name": "Scenario 1", "tasks": [...]},
    {"name": "Scenario 2", "tasks": [...]}
  ]
}
```

Each scenario can optionally override turn limits:

- **turn_limit**: Override the max turns for this specific scenario
- **turn_limit_per_task**: Override the max turns per task for this scenario

## Using Personalities

Personalities allow you to customize the communication style of the simulated user. This helps test how your agent handles different types of users.

Create a `personalities.json` file:

```json
[
  {
    "name": "Friendly Traveler",
    "description": "You are a friendly and enthusiastic person. You use casual language and show excitement about your travel plans. You often use exclamation marks and express gratitude."
  },
  {
    "name": "Business Professional",
    "description": "You are a business professional who is direct and efficient. You prefer concise communication and value your time. You use formal language and expect quick, accurate responses."
  },
  {
    "name": "Budget-Conscious Traveler",
    "description": "You are a budget-conscious traveler who is very price-sensitive. You frequently ask about costs, discounts, and budget-friendly options. You are detail-oriented and want to make sure you get the best value."
  }
]
```

When a personality is selected, its description is included in the system prompt for the simulated user, influencing how they phrase their messages.

## Running Simulations

To run a simulation, you need to:

1. Create a [`ChatInterface`][ragbits.chat.interface.ChatInterface] for your agent
2. Load scenarios and optionally personalities
3. Create a [`SimulationConfig`][ragbits.evaluate.agent_simulation.models.SimulationConfig]
4. Call [`run_simulation`][ragbits.evaluate.agent_simulation.conversation.run_simulation]

### Basic Example

```python
import asyncio
from ragbits.chat.interface import ChatInterface
from ragbits.evaluate.agent_simulation import load_scenarios, run_simulation
from ragbits.evaluate.agent_simulation.models import SimulationConfig

# Create your chat interface (this wraps your agent)
class MyChat(ChatInterface):
    async def setup(self) -> None:
        # Initialize your agent here
        pass

    async def chat(self, message, history, context):
        # Your agent's chat implementation
        async for chunk in agent.run_streaming(message):
            if isinstance(chunk, str):
                yield chunk

# Load scenario
scenarios = load_scenarios("scenarios.json")
scenario = scenarios[0]

# Configure simulation
config = SimulationConfig(
    max_turns_scenario=15,
    max_turns_task=4,
    log_file="conversation.log",
    default_model="gpt-4o-mini",
    api_key="your-api-key",
)

# Run simulation
chat = MyChat()
await chat.setup()

result = await run_simulation(
    scenario=scenario,
    chat=chat,
    config=config,
)

# Access structured results
print(f"Status: {result.status.value}")
print(f"Success rate: {result.metrics.success_rate:.1%}")
print(f"Tasks completed: {result.metrics.tasks_completed}/{result.metrics.total_tasks}")
```

### With Personality

```python
from ragbits.evaluate.agent_simulation import load_personalities

# Load personality
personalities = load_personalities("personalities.json")
personality = personalities[0]

result = await run_simulation(
    scenario=scenario,
    chat=chat,
    config=config,
    personality=personality,
)
```

### Configuration Options

All simulation parameters are grouped in [`SimulationConfig`][ragbits.evaluate.agent_simulation.models.SimulationConfig]:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_turns_scenario` | `int` | `15` | Maximum conversation turns for the entire scenario |
| `max_turns_task` | `int \| None` | `4` | Maximum turns per task (`None` for no limit) |
| `log_file` | `str \| None` | `None` | Path to log file for conversation history |
| `agent_model_name` | `str \| None` | `None` | Override for agent LLM model |
| `sim_user_model_name` | `str \| None` | `None` | Override for simulated user LLM model |
| `checker_model_name` | `str \| None` | `None` | Override for checker LLM model |
| `default_model` | `str` | `"gpt-4o-mini"` | Default LLM model when specific models not set |
| `api_key` | `str` | `""` | API key for LLM |
| `user_message_prefix` | `str` | `""` | Prefix added to user messages before sending to agent |
| `domain_context` | `DomainContext \| None` | `None` | Domain context for checkers (currency, locale, rules) |
| `data_snapshot` | `DataSnapshot \| None` | `None` | Data snapshot to ground simulated user requests |
| `metrics` | `list \| None` | `None` | Additional metric collector factories |

The `run_simulation` function also accepts these keyword arguments:

- **personality**: Optional personality for the simulated user
- **progress_callback**: Optional async callback for real-time progress updates
- **output_stream**: Optional stream for simulation output (defaults to stdout)

### Using Different Models

Each component (agent, simulated user, checker) can use a different LLM model. If a specific model is not set, it falls back to `default_model`:

```python
config = SimulationConfig(
    default_model="gpt-4o-mini",           # fallback for all
    agent_model_name="gpt-4o",             # agent uses gpt-4o
    sim_user_model_name="gpt-4o-mini",     # simulated user uses gpt-4o-mini
    checker_model_name="gpt-4o-mini",      # checker uses gpt-4o-mini
    api_key="your-api-key",
)
```

## Checker System

The checker system is a pluggable framework for validating task completion. Each task can have multiple checkers that are combined using the `checker_mode`.

### Built-in Checker Types

#### LLM Checker (`"llm"`)

Uses an LLM to evaluate whether the task was completed based on conversation history and an expected result description:

```json
{"type": "llm", "expected_result": "Hotel booked with confirmation number"}
```

The LLM checker analyzes the conversation history and compares the assistant's responses against the expected result, returning a boolean decision with reasoning.

#### Tool Call Checker (`"tool_call"`)

Verifies that specific tools were called during the conversation turn:

```json
{"type": "tool_call", "tools": ["search_rooms", "create_reservation"], "mode": "all"}
```

- **tools**: List of expected tool names (strings or detailed `ToolCallExpectation` objects)
- **mode**: `"all"` (all tools must be called) or `"any"` (at least one). Defaults to `"all"`.

For detailed tool call verification, use `ToolCallExpectation` objects:

```json
{
  "type": "tool_call",
  "tools": [
    {"name": "create_reservation", "arguments": {"city": "Warsaw"}, "result_contains": "confirmed"}
  ]
}
```

#### State Checker (`"state"`)

Verifies that the conversation state contains expected values:

```json
{
  "type": "state",
  "checks": [
    {"key": "user.confirmed", "value": true},
    {"key": "booking.total", "min_value": 100, "max_value": 500}
  ],
  "mode": "all"
}
```

State expectations support: exact value matching, existence checks, substring matching (`contains`), and numeric range checks (`min_value`, `max_value`).

### Combining Checkers

Use `checker_mode` on the task to control how multiple checkers are combined:

```json
{
  "task": "book a hotel room",
  "checkers": [
    {"type": "llm", "expected_result": "Booking confirmed"},
    {"type": "tool_call", "tools": ["create_reservation"]}
  ],
  "checker_mode": "all"
}
```

- `"all"`: All checkers must pass (default)
- `"any"`: At least one checker must pass

### Custom Checkers

You can create custom checkers by subclassing `BaseCheckerConfig` and registering them:

```python
from ragbits.evaluate.agent_simulation.checkers import (
    BaseCheckerConfig,
    CheckerContext,
    CheckerResult,
    register_checker,
)

@register_checker("my_checker")
class MyCheckerConfig(BaseCheckerConfig):
    type: ClassVar[str] = "my_checker"
    threshold: float = 0.8

    async def check(self, task, history, tool_calls, state, context) -> CheckerResult:
        # Your custom validation logic
        score = compute_score(history)
        return CheckerResult(
            completed=score >= self.threshold,
            reason=f"Score: {score:.2f}",
            checker_type=self.type,
        )
```

Then use it in scenarios:

```json
{"type": "my_checker", "threshold": 0.9}
```

## Domain Context and Data Grounding

### Domain Context

`DomainContext` provides domain-specific information to checkers, helping avoid false negatives from locale or business rule differences:

```python
from ragbits.evaluate.agent_simulation.context import DomainContext

config = SimulationConfig(
    domain_context=DomainContext(
        domain_type="hotel_booking",
        locale="pl_PL",
        metadata={
            "currency": "PLN",
            "date_format": "YYYY-MM-DD",
        },
    ),
    ...
)
```

### Data Snapshot

`DataSnapshot` grounds the simulated user's requests to data that actually exists, preventing unrealistic requests:

```python
from ragbits.evaluate.agent_simulation.context import DataSnapshot

config = SimulationConfig(
    data_snapshot=DataSnapshot(
        description="Available hotels and rooms",
        entities={
            "cities": ["Warsaw", "Krakow", "Gdansk"],
            "room_types": ["standard", "deluxe", "suite"],
        },
    ),
    ...
)
```

## Metric Collectors

The simulation framework includes built-in metric collectors that always run:

- **LatencyMetricCollector**: Tracks response latency per turn (avg, min, max, time to first token)
- **TokenUsageMetricCollector**: Tracks token usage and estimated cost
- **ToolUsageMetricCollector**: Tracks tool call patterns (total calls, unique tools, per-turn)

You can add additional custom metric collectors via `SimulationConfig.metrics`:

```python
from ragbits.evaluate.agent_simulation.metrics import (
    LatencyMetricCollector,
    TokenUsageMetricCollector,
)

config = SimulationConfig(
    metrics=[LatencyMetricCollector, TokenUsageMetricCollector],
    ...
)
```

Metrics are passed as classes (or callables returning instances). Fresh instances are created for each run. All metrics end up in the flat `result.metrics.metrics` dictionary.

### Creating Custom Metric Collectors

Subclass `MetricCollector` to track custom metrics:

```python
from ragbits.evaluate.agent_simulation.metrics import MetricCollector

class MyMetricCollector(MetricCollector):
    def __init__(self):
        self._count = 0

    def on_turn_end(self, turn_result):
        if turn_result.task_completed:
            self._count += 1

    def on_conversation_end(self, all_turns):
        return {"my_custom_metric": self._count}
```

## Structured Results

`run_simulation` returns a [`SimulationResult`][ragbits.evaluate.agent_simulation.results.SimulationResult] object containing:

### SimulationResult

- **scenario_name**: Name of the scenario
- **start_time** / **end_time**: Timestamps
- **status**: One of `completed`, `failed`, `timeout`
- **turns**: List of `TurnResult` objects
- **tasks**: List of `TaskResult` objects
- **metrics**: `ConversationMetrics` with aggregated data
- **traces**: Captured execution traces
- **error**: Error message if simulation failed
- **persona**: Name of the personality used (if any)

### Working with Results

```python
result = await run_simulation(scenario=scenario, chat=chat)

# Check status
if result.status == SimulationStatus.COMPLETED:
    print("All tasks completed successfully!")

# Access metrics (flat dictionary)
metrics = result.metrics.metrics
print(f"Total turns: {result.metrics.total_turns}")
print(f"Success rate: {result.metrics.success_rate:.1%}")
print(f"Tokens used: {metrics.get('tokens_total', 0)}")
print(f"Estimated cost: ${metrics.get('estimated_usd', 0):.4f}")

# Iterate over tasks
for task in result.tasks:
    status = "PASS" if task.completed else "FAIL"
    print(f"[{status}] Task {task.task_index}: {task.description}")
    print(f"  Turns taken: {task.turns_taken}")
    print(f"  Reason: {task.final_reason}")

# Iterate over turns
for turn in result.turns:
    print(f"Turn {turn.turn_index} (Task {turn.task_index})")
    print(f"  User: {turn.user_message}")
    print(f"  Assistant: {turn.assistant_message}")
    if turn.tool_calls:
        print(f"  Tools: {[tc['name'] for tc in turn.tool_calls]}")
    if turn.checkers:
        for checker in turn.checkers:
            print(f"  Checker [{checker.type}]: {'PASS' if checker.completed else 'FAIL'} - {checker.reason}")

# Serialize to JSON
import json
with open("results.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)

# Load from JSON
with open("results.json") as f:
    loaded_result = SimulationResult.from_dict(json.load(f))
```

## How It Works

The simulation follows this flow:

1. **Initialization**: The simulated user, checker context, and metric collectors are created from the `SimulationConfig`
2. **Task Selection**: The simulated user selects the first task from the scenario
3. **Conversation Loop**:
   - Simulated user generates a message based on the current task (and personality, if specified)
   - Your agent processes the message and may call tools
   - Configured checkers evaluate whether the task is complete
   - If all/any checkers pass (depending on `checker_mode`), move to the next task
   - Otherwise, continue the conversation
   - The conversation stops when all tasks are completed, the per-task turn limit is exceeded, or the scenario turn limit is reached
4. **Logging**: All turns, tool calls, checker results, and task completions are logged
5. **Metrics**: Built-in and custom metric collectors aggregate results
6. **Results**: Structured `SimulationResult` is returned for programmatic access

## DeepEval Integration

The simulation can optionally evaluate conversations using DeepEval metrics:

- **ConversationCompletenessMetric**: Measures how complete the conversation is
- **KnowledgeRetentionMetric**: Evaluates how well the agent retains information across turns
- **ConversationRelevancyMetric**: Assesses the relevance of responses to the conversation

## Logging

The [`ConversationLogger`][ragbits.evaluate.agent_simulation.logger.ConversationLogger] records:

- Session metadata (scenario, models used, personality)
- Each conversation turn (user message, assistant response, tool calls)
- Checker results for each turn
- Token usage and estimated costs

Log files are written in a structured format that can be analyzed later.

## Complete Example

Here's a complete example using the hotel booking scenario:

```python
import asyncio
import json
from ragbits.chat.interface import ChatInterface
from ragbits.evaluate.agent_simulation import (
    load_personalities,
    load_scenarios,
    run_simulation,
    SimulationStatus,
)
from ragbits.evaluate.agent_simulation.models import SimulationConfig

# Assuming you have a HotelChat class that implements ChatInterface
from fixtures.hotel.hotel_chat import HotelChat

async def main() -> None:
    # Load scenario and personality
    scenarios = load_scenarios("scenarios.json")
    scenario = scenarios[0]

    personalities = load_personalities("personalities.json")
    personality = personalities[0]  # Optional

    # Create chat interface
    hotel_chat = HotelChat(model_name="gpt-4o-mini", api_key="your-api-key")
    await hotel_chat.setup()

    # Configure simulation
    config = SimulationConfig(
        max_turns_scenario=15,
        max_turns_task=4,
        log_file="hotel_booking_conversation.log",
        default_model="gpt-4o-mini",
        api_key="your-api-key",
        user_message_prefix=(
            "[STYLE]\nAnswer helpfully and clearly. "
            "Provide specific details when available.\n\n"
        ),
    )

    # Run simulation
    result = await run_simulation(
        scenario=scenario,
        chat=hotel_chat,
        config=config,
        personality=personality,
    )

    # Print summary
    print(f"\nSimulation completed with status: {result.status.value}")
    if result.metrics:
        print(f"Tasks completed: {result.metrics.tasks_completed}/{result.metrics.total_tasks}")
        print(f"Success rate: {result.metrics.success_rate:.1%}")

    # Save results
    with open("simulation_results.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
```

## Command-Line Usage

You can also run simulations from the command line using the example CLI:

```bash
uv run python examples/evaluate/agent-scenarios/hotel_simulation.py \
  --scenario-id 1 \
  --max-turns-scenario 15 \
  --max-turns-task 4 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file conversation.log \
  --scenarios-file scenarios.json \
  --persona-id 1 \
  --personas-file personalities.json \
  --output-json results.json
```

## Best Practices

1. **Start Simple**: Begin with simple scenarios and gradually add complexity
2. **Use Multiple Checkers**: Combine `llm` and `tool_call` checkers for thorough validation
3. **Test Different Personalities**: Use different personalities to test how your agent handles various user types
4. **Monitor Logs**: Review log files to understand agent behavior and identify issues
5. **Iterate on Scenarios**: Refine scenarios based on evaluation results
6. **Set Appropriate Limits**: Use `max_turns_task` and `max_turns_scenario` to prevent infinite loops
7. **Use Structured Results**: Leverage `SimulationResult` for programmatic analysis and aggregation
8. **Ground with Data**: Use `DataSnapshot` to prevent simulated users from requesting non-existent data

## See Also

- [Evaluate pipelines](evaluate.md) - General evaluation framework
- [Create custom evaluation pipeline](custom_evaluation_pipeline.md) - Building custom evaluation pipelines
- Example implementation: `examples/evaluate/agent-scenarios/`
