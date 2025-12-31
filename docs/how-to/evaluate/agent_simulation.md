# How-To: Agent Simulation for Evaluation

Agent simulation allows you to evaluate your agents by having them interact with a simulated user in realistic conversation scenarios. This is particularly useful for testing agent behavior, tool usage, and task completion in a controlled environment.

## Overview

The agent simulation framework consists of several key components:

- **Simulated User**: An LLM-driven user that generates realistic messages based on tasks and conversation history
- **Goal Checker**: An LLM-based judge that evaluates whether tasks have been completed successfully
- **Tool Usage Checker**: Verifies that agents use the expected tools for each task
- **Conversation Logger**: Records all conversation turns, tool calls, and evaluation results
- **DeepEval Integration**: Automatic evaluation of conversation quality using DeepEval metrics
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
        "expected_result": "{list of hotels in Warsaw}",
        "expected_tools": ["list_hotels"]
      },
      {
        "task": "check availability for 3 nights from April 1, 2025",
        "expected_result": "{available rooms for specified dates}",
        "expected_tools": ["search_available_rooms"]
      },
      {
        "task": "book a budget-friendly room",
        "expected_result": "{booking confirmation}",
        "expected_tools": ["create_reservation"]
      }
    ]
  }
]
```

Each task has:
- **task**: Description of what the user wants to accomplish
- **expected_result**: What should happen when the task is completed
- **expected_tools** (optional): List of tool names that should be used to complete this task

When `expected_tools` is specified, the system will verify that all expected tools were called during the conversation turn.

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
3. Call [`run_simulation`][ragbits.evaluate.agent_simulation.conversation.run_simulation]

### Basic Example

```python
import asyncio
from ragbits.chat.interface import ChatInterface
from ragbits.evaluate.agent_simulation import load_scenarios, run_simulation

# Create your chat interface (this wraps your agent)
class MyChat(ChatInterface):
    async def setup(self) -> None:
        # Initialize your agent here
        pass

    async def chat(self, message: str, history, context):
        # Your agent's chat implementation
        async for chunk in agent.run_streaming(message):
            if isinstance(chunk, str):
                yield chunk

# Load scenario
scenarios = load_scenarios("scenarios.json")
scenario = scenarios[0]  # Use first scenario

# Run simulation
chat = MyChat()
await chat.setup()

result = await run_simulation(
    scenario=scenario,
    chat=chat,
    max_turns_scenario=15,
    max_turns_task=4,
    log_file="conversation.log",
    default_model="gpt-4o-mini",
    api_key="your-api-key",
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
personality = personalities[0]  # Use first personality

result = await run_simulation(
    scenario=scenario,
    chat=chat,
    personality=personality,
    max_turns_scenario=15,
    max_turns_task=4,
    log_file="conversation.log",
    default_model="gpt-4o-mini",
    api_key="your-api-key",
)
```

### Configuration Options

[`run_simulation`][ragbits.evaluate.agent_simulation.conversation.run_simulation] accepts several configuration options:

- **scenario**: The scenario containing tasks to complete (required)
- **chat**: Your ChatInterface instance (required)
- **max_turns_scenario**: Maximum number of conversation turns for the entire scenario (default: 15)
- **max_turns_task**: Maximum number of conversation turns per task (default: 4, None for no limit)
- **log_file**: Optional path to log file for conversation history
- **agent_model_name**: Optional override for agent LLM model name
- **sim_user_model_name**: Optional override for simulated user LLM model name
- **checker_model_name**: Optional override for goal checker LLM model name
- **default_model**: Default LLM model name (default: "gpt-4o-mini")
- **api_key**: API key for LLM
- **user_message_prefix**: Optional prefix to add to user messages before sending to agent
- **personality**: Optional personality to use for the simulated user

## Structured Results

`run_simulation` returns a [`SimulationResult`][ragbits.evaluate.agent_simulation.results.SimulationResult] object containing:

### SimulationResult

- **scenario_name**: Name of the scenario
- **start_time** / **end_time**: Timestamps
- **status**: One of `completed`, `failed`, `timeout`
- **turns**: List of `TurnResult` objects
- **tasks**: List of `TaskResult` objects
- **metrics**: `ConversationMetrics` with aggregated data
- **error**: Error message if simulation failed

### Working with Results

```python
result = await run_simulation(scenario=scenario, chat=chat)

# Check status
if result.status == SimulationStatus.COMPLETED:
    print("All tasks completed successfully!")

# Access metrics
print(f"Total turns: {result.metrics.total_turns}")
print(f"Total tokens: {result.metrics.total_tokens}")
print(f"Total cost: ${result.metrics.total_cost_usd:.4f}")
print(f"Success rate: {result.metrics.success_rate:.1%}")

# Iterate over tasks
for task in result.tasks:
    status = "✓" if task.completed else "✗"
    print(f"{status} Task {task.task_index}: {task.description}")
    print(f"  Turns taken: {task.turns_taken}")
    print(f"  Reason: {task.final_reason}")

# Iterate over turns
for turn in result.turns:
    print(f"Turn {turn.turn_index} (Task {turn.task_index})")
    print(f"  User: {turn.user_message}")
    print(f"  Assistant: {turn.assistant_message}")
    if turn.tool_calls:
        print(f"  Tools: {[tc['name'] for tc in turn.tool_calls]}")

# Access DeepEval scores
for metric, score in result.metrics.deepeval_scores.items():
    print(f"{metric}: {score:.4f}")

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

1. **Initialization**: The simulated user, goal checker, and tool usage checker are created
2. **Task Selection**: The simulated user selects the first task from the scenario
3. **Conversation Loop**:
   - Simulated user generates a message based on the current task (and personality, if specified)
   - Your agent processes the message and may call tools
   - Tool usage checker verifies expected tools were used (if `expected_tools` is specified)
   - Goal checker evaluates if the task is complete
   - If complete, move to the next task; otherwise, continue the conversation
   - The conversation stops when all tasks are completed, the per-task turn limit (`max_turns_task`) is exceeded, or the scenario turn limit (`max_turns_scenario`) is reached
4. **Logging**: All turns, tool calls, tool usage checks, task completions, and the selected personality (if any) are logged to a file
5. **Evaluation**: DeepEval metrics are automatically computed at the end
6. **Results**: Structured `SimulationResult` is returned for programmatic access

## Goal Checking

The [`GoalChecker`][ragbits.evaluate.agent_simulation.simulation.GoalChecker] uses an LLM to determine if a task has been completed. It inspects the conversation history and checks if the task matches the expected result.

The goal checker:
- Analyzes the conversation history
- Compares the assistant's responses against the expected result
- Returns a boolean indicating completion and a reason

## Tool Usage Validation

The [`ToolUsageChecker`][ragbits.evaluate.agent_simulation.simulation.ToolUsageChecker] verifies that your agent used the expected tools for each task.

When `expected_tools` is specified in a task:
- The system tracks all tool calls made during the conversation turn
- Verifies that all expected tools were used
- Logs the results and displays feedback in the console

## DeepEval Integration

The simulation automatically evaluates conversations using DeepEval metrics:

- **ConversationCompletenessMetric**: Measures how complete the conversation is
- **KnowledgeRetentionMetric**: Evaluates how well the agent retains information across turns
- **ConversationRelevancyMetric**: Assesses the relevance of responses to the conversation

These metrics are computed at the end of the simulation and included in `result.metrics.deepeval_scores`.

## Logging

The [`ConversationLogger`][ragbits.evaluate.agent_simulation.logger.ConversationLogger] records:

- Session metadata (scenario, models used, personality)
- Each conversation turn (user message, assistant response, tool calls)
- Task completion checks
- Tool usage verification
- Token usage and estimated costs
- DeepEval evaluation metrics

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

    # Run simulation
    result = await run_simulation(
        scenario=scenario,
        chat=hotel_chat,
        max_turns_scenario=15,
        max_turns_task=4,
        log_file="hotel_booking_conversation.log",
        personality=personality,
        default_model="gpt-4o-mini",
        api_key="your-api-key",
        user_message_prefix=(
            "[STYLE]\nAnswer helpfully and clearly. "
            "Provide specific details when available (hotel names, room types, prices, dates). "
            "If information is unavailable, explain why briefly.\n\n"
        ),
    )

    # Print summary
    print(f"\nSimulation completed with status: {result.status.value}")
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
uv run python examples/evaluate/agent-scenarios/duet_cli.py \
  --scenario-id 1 \
  --max-turns-scenario 15 \
  --max-turns-task 4 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file conversation.log \
  --scenarios-file scenarios.json \
  --personality-id 1 \
  --personalities-file personalities.json \
  --output-json results.json
```

## Best Practices

1. **Start Simple**: Begin with simple scenarios and gradually add complexity
2. **Use Expected Tools**: Specify `expected_tools` to verify your agent uses the correct tools
3. **Test Different Personalities**: Use different personalities to test how your agent handles various user types
4. **Monitor Logs**: Review log files to understand agent behavior and identify issues
5. **Iterate on Scenarios**: Refine scenarios based on evaluation results
6. **Set Appropriate Limits**: Use `max_turns_task` and `max_turns_scenario` to prevent infinite loops
7. **Use Structured Results**: Leverage `SimulationResult` for programmatic analysis and aggregation

## See Also

- [Evaluate pipelines](evaluate.md) - General evaluation framework
- [Create custom evaluation pipeline](custom_evaluation_pipeline.md) - Building custom evaluation pipelines
- Example implementation: `examples/evaluate/agent-scenarios/`

