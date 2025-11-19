# Agent Scenarios: Human-to-Agent Conversation Example

This example demonstrates agent-to-agent communication using a simulated user and a goal checker to evaluate task completion. It showcases how to build a conversational agent that interacts with a simulated human user through a series of tasks.

## Overview

The Agent Scenarios example consists of:

- **Hotel Booking Agent**: A ragbits agent that uses hotel booking tools to help users find and book hotel rooms
- **Simulated User**: An LLM-driven user simulator that generates realistic user messages based on tasks
- **Goal Checker**: An LLM-based judge that evaluates whether tasks have been completed successfully

## Prerequisites

1. The hotel API service must be running (see [Hotel API README](fixtures/hotel-api/README.md))
2. An OpenAI API key must be set in your environment or `.env` file

## Quick Start

### 1. Start the Hotel API

In a separate terminal, start the hotel API service:

From the project root:

```bash
cd examples/evaluate/agent-scenarios/fixtures/hotel-api
uv run python populate_db.py  # First time setup
uv run uvicorn app:app --reload --port 8000
uv run python clear_db.py # Clear the hotel api database
```


### 2. Run the Agent Scenarios Example

From the project root:

```bash
uv run python examples/evaluate/agent-scenarios/duet_cli.py \
  --scenario-id 1 \
  --max-turns 10 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file examples/evaluate/agent-scenarios/duet_conversation.log \
  --scenarios-file examples/evaluate/agent-scenarios/scenarios.json
```

## Command-Line Options

- `--scenario-id` (required): Select a scenario from scenarios.json (1, 2, 3, or 4)
- `--scenarios-file`: Path to scenarios file (default: `scenarios.json`)
- `--max-turns`: Maximum number of conversation turns (default: 10)
- `--log-file`: Path to log file for conversation history (default: `duet_conversations.log`)
- `--agent-model-name`: LLM model for the hotel booking agent (defaults to `config.llm_model`)
- `--sim-user-model-name`: LLM model for the simulated user (defaults to `config.llm_model`)
- `--checker-model-name`: LLM model for the goal checker (defaults to `config.llm_model`)

## Scenarios

Scenarios are defined in `scenarios.json`. Each scenario contains:

- **name**: Descriptive name for the scenario
- **tasks**: List of tasks to complete sequentially
  - **task**: Description of what the user wants to accomplish
  - **expected_result**: What should happen when the task is completed

Example scenario:
```json
{
  "name": "Scenario 1",
  "tasks": [
    {
      "task": "are there rooms available in Krakow on 2025-06-01",
      "expected_result": "{list of available rooms}"
    },
    {
      "task": "are there delux rooms",
      "expected_result": "{list of rooms}"
    },
    {
      "task": "book room",
      "expected_result": "{book room}"
    }
  ]
}
```

## How It Works

1. **Initialization**: The hotel booking agent is created with hotel booking tools from the shared `fixtures.hotel` module
2. **Task Selection**: The simulated user selects the first task from the scenario
3. **Conversation Loop**:
   - Simulated user generates a message based on the current task
   - Hotel booking agent processes the message and may call tools
   - Goal checker evaluates if the task is complete
   - If complete, move to the next task; otherwise, continue the conversation
4. **Logging**: All turns and task completions are logged to a file

## Architecture

The example uses shared components from `fixtures/hotel/`:

- **Tools** (`fixtures/hotel/tools.py`): Hotel API client functions
- **Prompt** (`fixtures/hotel/prompt.py`): Hotel booking assistant prompt template

This modular design allows the hotel booking functionality to be reused across different examples.

## Files

- `duet_cli.py` - Main CLI application for running conversations
- `scenarios.json` - Task scenarios for testing
- `config.py` - Configuration settings (LLM model, API keys, etc.)
- `README.md` - This file

## Integration

This example integrates with:

- **Hotel API** (`fixtures/hotel-api/`): The backend service providing hotel data
- **Shared Hotel Module** (`fixtures/hotel/`): Reusable hotel booking tools and prompts

