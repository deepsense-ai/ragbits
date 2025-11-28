# Agent Scenarios: Human-to-Agent Conversation Example

This example demonstrates agent-to-agent communication using a simulated user and a goal checker to evaluate task completion. It showcases how to build a conversational agent that interacts with a simulated human user through a series of tasks.

## Overview

The Agent Scenarios example consists of:

- **Hotel Booking Agent**: A ragbits agent that uses hotel booking tools to help users find and book hotel rooms
- **Simulated User**: An LLM-driven user simulator that generates realistic user messages based on tasks
- **Goal Checker**: An LLM-based judge that evaluates whether tasks have been completed successfully
- **Tool Usage Checker**: An LLM-based evaluator that verifies the agent is using the expected tools for each task

## Prerequisites

1. The hotel API service must be running (see [Hotel API README](fixtures/hotel-api/README.md))
2. An OpenAI API key must be set in your environment or `.env` file

## Quick Start

### 1. Start the Hotel API (optional)

The duet CLI now bootstraps the Hotel API automatically: it seeds the database for every process id it needs (based on the scenarios you select), runs the API server, waits for it to become healthy, and shuts it down once all runs finish. You only need to start the API manually if you want to inspect or interact with it directly.

To start it manually, use the helper script (from the project root):

```bash
cd examples/evaluate/agent-scenarios/fixtures/hotel-api
uv run python populate_db.py  --ids 1 2 3 4 # First time setup, remember ids are potential process ids not scenario ids
uv run uvicorn app:app --reload --port 8000
uv run python clear_db.py # Clear the hotel api database
```


### 2. Run the Agent Scenarios Example

From the project root:

```bash
uv run python examples/evaluate/agent-scenarios/duet_cli.py \
  --scenario-ids 1 \
  --max-turns-scenario 15 \
  --max-turns-task 4 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file examples/evaluate/agent-scenarios/duet_conversation.log \
  --scenarios-file examples/evaluate/agent-scenarios/scenarios.json
```

> **Note:** During startup the CLI populates the database for each internal process id (one per selected scenario/personality pair), launches `uvicorn`, and waits for `http://localhost:8000/openapi.json` to respond before the agent interactions begin. When all batches finish the server process is shut down automatically.

> After the runs complete the CLI also invokes `clear_db.py` to drop all namespaced tables and delete the SQLite file, so each invocation starts from a clean slate. If you want to keep the data for debugging, interrupt the CLI before it reaches the cleanup step.

To run multiple scenarios or to use specific personalities for the simulated user:

```bash
uv run python examples/evaluate/agent-scenarios/duet_cli.py \
  --scenario-ids 1 2 3 \
  --max-turns-scenario 15 \
  --max-turns-task 4 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file examples/evaluate/agent-scenarios/duet_conversation.log \
  --scenarios-file examples/evaluate/agent-scenarios/scenarios.json \
  --personality-ids 1 2 3 \
  --personalities-file examples/evaluate/agent-scenarios/personalities.json \
  --batch-size 2
```

## Command-Line Options

- `--scenario-ids` (required): Select one or more scenarios from scenarios.json (1-based indices). Pass several IDs separated by space to run multiple scenarios.
- `--scenarios-file`: Path to scenarios file (default: `scenarios.json`)
- `--personality-ids` (optional): Select zero or more personalities from personalities.json (1-based indices). When provided, personality IDs will be paired with `--scenario-ids` one-to-one (missing personality ids will be treated as None). If fewer personality ids are provided than scenarios, the remaining scenarios will use the default simulated user behavior.
- `--personalities-file`: Path to personalities file (default: `personalities.json`)
- `--max-turns-scenario`: Maximum number of conversation turns for the entire scenario (default: 15). If exceeded, the conversation exits
- `--max-turns-task`: Maximum number of conversation turns per task (default: 4). If exceeded, the conversation exits (same behavior as max_turns_scenario)
- `--log-file`: Path to log file for conversation history (default: `duet_conversations.log`)
- `--agent-model-name`: LLM model for the hotel booking agent (defaults to `config.llm_model`)
- `--sim-user-model-name`: LLM model for the simulated user (defaults to `config.llm_model`)
- `--checker-model-name`: LLM model for the goal checker (defaults to `config.llm_model`)
 - `--batch-size`: How many scenario runs to execute concurrently (default: 2). Useful when running multiple scenarios in parallel to control resource usage.

## Scenarios

Scenarios are defined in `scenarios.json`. Each scenario contains:

- **name**: Descriptive name for the scenario
- **tasks**: List of tasks to complete sequentially
  - **task**: Description of what the user wants to accomplish
  - **expected_result**: What should happen when the task is completed
  - **expected_tools** (optional): List of tool names that should be used to complete this task

Example scenario:
```json
{
  "name": "Scenario 1",
  "tasks": [
    {
      "task": "are there rooms available in Krakow on 2025-06-01",
      "expected_result": "{list of available rooms}",
      "expected_tools": ["search_available_rooms"]
    },
    {
      "task": "are there delux rooms",
      "expected_result": "{list of rooms}",
      "expected_tools": ["search_available_rooms"]
    },
    {
      "task": "book room",
      "expected_result": "{book room}",
      "expected_tools": ["create_reservation"]
    }
  ]
}
```

When `expected_tools` is specified, the system will:
- Track all tool calls made during the conversation turn
- Verify that all expected tools were used
- Use an LLM to evaluate if the tool usage was appropriate for the task
- Log the results and display feedback in the console

## Personalities

Personalities are defined in `personalities.json` and allow you to customize the behavior and communication style of the simulated user. Each personality has:

- **name**: Descriptive name for the personality
- **description**: Instructions that modify how the simulated user communicates (e.g., formal vs. casual, budget-conscious vs. luxury-focused)

Example personality:
```json
{
  "name": "Personality 1",
  "description": "You are a friendly and enthusiastic person. You use casual language and show excitement about your travel plans. You often use exclamation marks and express gratitude."
}
```

When a personality is selected via `--personality-ids` (or when one personality id is supplied), the personality description is included in the system prompt for the simulated user, influencing how they phrase their messages and interact with the agent. If no personality id is supplied for a given scenario, the simulated user will use default behavior without any personality-specific instructions.

Note about logs when running multiple scenarios concurrently: if you provide a `--log-file` path and run multiple scenarios in parallel, the CLI will append a per-run suffix to avoid write conflicts. Example: `duet_conversation.log.pid1_s1_p1` (process id, scenario id, personality id).

Available hotel booking tools:
- `list_cities` - Get a list of all available cities
- `list_hotels` - List hotels, optionally filtered by city
- `get_hotel_details` - Get detailed information about a specific hotel
- `search_available_rooms` - Search for available rooms with filters (dates, city, price, room type)
- `create_reservation` - Create a new hotel reservation
- `list_reservations` - List reservations, optionally filtered by guest name
- `get_reservation` - Get details of a specific reservation
- `cancel_reservation` - Cancel a reservation

## How It Works

1. **Initialization**: The hotel booking agent is created with hotel booking tools from the shared `fixtures.hotel` module. If a personality is specified, it is loaded and will influence the simulated user's communication style.
2. **Task Selection**: The simulated user selects the first task from the scenario
3. **Conversation Loop**:
   - Simulated user generates a message based on the current task (and personality, if specified)
   - Hotel booking agent processes the message and may call tools
   - Tool usage checker verifies expected tools were used (if `expected_tools` is specified)
   - Goal checker evaluates if the task is complete
   - If complete, move to the next task; otherwise, continue the conversation
   - The conversation stops when all tasks are completed, the per-task turn limit (`max_turns_task`) is exceeded, or the scenario turn limit (`max_turns_scenario`) is reached
4. **Logging**: All turns, tool calls, tool usage checks, task completions, and the selected personality (if any) are logged to a file

## Architecture

The example uses shared components from `fixtures/hotel/`:

- **Tools** (`fixtures/hotel/tools.py`): Hotel API client functions
- **Prompt** (`fixtures/hotel/prompt.py`): Hotel booking assistant prompt template

This modular design allows the hotel booking functionality to be reused across different examples.

## Files

- `duet_cli.py` - Main CLI application for running conversations
- `scenarios.json` - Task scenarios for testing
- `personalities.json` - Personality definitions for the simulated user
- `config.py` - Configuration settings (LLM model, API keys, etc.)
- `README.md` - This file

## Integration

This example integrates with:

- **Hotel API** (`fixtures/hotel-api/`): The backend service providing hotel data
- **Shared Hotel Module** (`fixtures/hotel/`): Reusable hotel booking tools and prompts

