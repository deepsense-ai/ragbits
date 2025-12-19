"""Scenario loading functionality for agent simulation."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task


@dataclass
class ScenarioFile:
    """Represents a loaded scenario file with its metadata."""

    filename: str
    group: str | None
    scenarios: list[Scenario] = field(default_factory=list)


def load_scenarios(scenarios_file: str = "scenarios.json") -> list[Scenario]:
    """Load scenarios from a JSON file.

    Expected JSON format (new format with file-level group):
    {
      "group": "Group Name",
      "scenarios": [
        {
          "name": "Scenario 1",
          "tasks": [
            {
              "task": "task description",
              "checkers": [
                {"type": "llm", "expected_result": "expected result"},
                {"type": "tool_call", "tools": ["tool1", "tool2"]},
                {"type": "state", "checks": [{"key": "user.confirmed", "value": true}]}
              ],
              "checker_mode": "all"
            },
            ...
          ]
        },
        ...
      ]
    }

    Legacy format (array of scenarios) is still supported:
    [
      {
        "name": "Scenario 1",
        "tasks": [...]
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
    scenario_file = load_scenario_file(scenarios_file)
    return scenario_file.scenarios


def load_scenario_file(scenarios_file: str = "scenarios.json") -> ScenarioFile:
    """Load scenarios from a JSON file with file-level metadata.

    This function supports both the new format with file-level group:
    {
      "group": "Group Name",
      "scenarios": [...]
    }

    And the legacy format (array of scenarios):
    [
      {"name": "Scenario 1", "tasks": [...]},
      ...
    ]

    Args:
        scenarios_file: Path to the JSON file containing scenarios

    Returns:
        ScenarioFile object containing scenarios and file-level metadata

    Raises:
        FileNotFoundError: If the scenarios file doesn't exist
        ValueError: If the file format is invalid
    """
    scenarios_path = Path(scenarios_file)
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_path}")

    with scenarios_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Determine format and extract scenarios data and file-level group
    file_group: str | None = None
    scenarios_data: list

    if isinstance(data, dict):
        # New format: {"group": "...", "scenarios": [...]}
        file_group = data.get("group")
        scenarios_data = data.get("scenarios", [])
        if not isinstance(scenarios_data, list):
            raise ValueError(f"'scenarios' field must be a JSON array, got {type(scenarios_data).__name__}")
    elif isinstance(data, list):
        # Legacy format: [...]
        scenarios_data = data
    else:
        raise ValueError(f"Scenarios file must contain a JSON object or array, got {type(data).__name__}")

    scenarios: list[Scenario] = []
    for scenario_data in scenarios_data:
        if not isinstance(scenario_data, dict):
            raise ValueError(f"Each scenario must be a JSON object, got {type(scenario_data).__name__}")

        name = scenario_data.get("name", "")
        tasks_data = scenario_data.get("tasks", [])
        # Scenario can have its own group, or inherit from file-level group
        scenario_group = scenario_data.get("group") or file_group

        if not isinstance(tasks_data, list):
            raise ValueError(f"Tasks must be a JSON array, got {type(tasks_data).__name__}")

        tasks: list[Task] = []
        for task_data in tasks_data:
            if not isinstance(task_data, dict):
                raise ValueError(f"Each task must be a JSON object, got {type(task_data).__name__}")

            task_desc = task_data.get("task", "")
            checkers = task_data.get("checkers", [])
            checker_mode = task_data.get("checker_mode", "all")

            if not isinstance(checkers, list):
                raise ValueError(f"checkers must be a list, got {type(checkers).__name__}")

            tasks.append(Task(task=task_desc, checkers=checkers, checker_mode=checker_mode))

        scenarios.append(Scenario(name=name, tasks=tasks, group=scenario_group))

    if not scenarios:
        raise ValueError(f"No scenarios found in {scenarios_path}")

    return ScenarioFile(
        filename=scenarios_path.name,
        group=file_group,
        scenarios=scenarios,
    )


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
