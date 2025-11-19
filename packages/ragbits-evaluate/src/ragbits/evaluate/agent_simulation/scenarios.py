"""Scenario loading functionality for agent simulation."""

from __future__ import annotations

import json
from pathlib import Path

from ragbits.evaluate.agent_simulation.models import Scenario, Task


def load_scenarios(scenarios_file: str = "scenarios.json") -> list[Scenario]:
    """Load scenarios from a JSON file.

    Expected JSON format:
    [
      {
        "name": "Scenario 1",
        "tasks": [
          {
            "task": "task description",
            "expected_result": "expected result description"
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
            tasks.append(Task(task=task_desc, expected_result=expected_result))

        scenarios.append(Scenario(name=name, tasks=tasks))

    if not scenarios:
        raise ValueError(f"No scenarios found in {scenarios_path}")

    return scenarios
