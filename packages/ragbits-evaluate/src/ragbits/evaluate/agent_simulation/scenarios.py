"""Scenario loading functionality for agent simulation."""

import json
from pathlib import Path

from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task


def load_scenarios(scenarios_file: str = "scenarios.json") -> list[Scenario]:
    """Load scenarios from a JSON file.

    Expected JSON format:
    [
      {
        "name": "Scenario 1",
        "tasks": [
          {
            "task": "task description",
            "expected_result": "expected result description",
            "expected_tools": ["tool1", "tool2"]  # optional
          },
          ...
        ]
      },
      ...
    ]

    Args:
        scenarios_file: Path to the JSON file containing scenarios

    Returns:
        List of Scenario objects

    Raises:
        FileNotFoundError: If the scenarios file doesn't exist
        ValueError: If the file format is invalid
    """
    scenarios_path = Path(scenarios_file)
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_path}")

    with scenarios_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Scenarios file must contain a JSON array, got {type(data).__name__}")

    scenarios: list[Scenario] = []
    for scenario_data in data:
        if not isinstance(scenario_data, dict):
            raise ValueError(f"Each scenario must be a JSON object, got {type(scenario_data).__name__}")

        name = scenario_data.get("name", "")
        tasks_data = scenario_data.get("tasks", [])

        if not isinstance(tasks_data, list):
            raise ValueError(f"Tasks must be a JSON array, got {type(tasks_data).__name__}")

        tasks: list[Task] = []
        for task_data in tasks_data:
            if not isinstance(task_data, dict):
                raise ValueError(f"Each task must be a JSON object, got {type(task_data).__name__}")

            task_desc = task_data.get("task", "")
            expected_result = task_data.get("expected_result", "")
            expected_tools = task_data.get("expected_tools")
            if expected_tools is not None and not isinstance(expected_tools, list):
                raise ValueError(f"expected_tools must be a list or null, got {type(expected_tools).__name__}")
            tasks.append(Task(task=task_desc, expected_result=expected_result, expected_tools=expected_tools))

        scenarios.append(Scenario(name=name, tasks=tasks))

    if not scenarios:
        raise ValueError(f"No scenarios found in {scenarios_path}")

    return scenarios


def load_personalities(personalities_file: str = "personalities.json") -> list[Personality]:
    """Load personalities from a JSON file.

    Expected JSON format:
    [
      {
        "name": "Personality 1",
        "description": "Personality description that will be used in the system prompt"
      },
      ...
    ]

    Args:
        personalities_file: Path to the JSON file containing personalities

    Returns:
        List of Personality objects

    Raises:
        FileNotFoundError: If the personalities file doesn't exist
        ValueError: If the file format is invalid
    """
    personalities_path = Path(personalities_file)
    if not personalities_path.exists():
        raise FileNotFoundError(f"Personalities file not found: {personalities_path}")

    with personalities_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Personalities file must contain a JSON array, got {type(data).__name__}")

    personalities: list[Personality] = []
    for personality_data in data:
        if not isinstance(personality_data, dict):
            raise ValueError(f"Each personality must be a JSON object, got {type(personality_data).__name__}")

        name = personality_data.get("name", "")
        description = personality_data.get("description", "")

        if not name:
            raise ValueError("Each personality must have a 'name' field")
        if not description:
            raise ValueError("Each personality must have a 'description' field")

        personalities.append(Personality(name=name, description=description))

    if not personalities:
        raise ValueError(f"No personalities found in {personalities_path}")

    return personalities
