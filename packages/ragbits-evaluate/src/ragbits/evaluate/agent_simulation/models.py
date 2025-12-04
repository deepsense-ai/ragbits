"""Data models for agent simulation scenarios."""

from dataclasses import dataclass


@dataclass
class Turn:
    """A single conversation turn between user and assistant."""

    user: str
    assistant: str


@dataclass
class Task:
    """A single task with its expected result."""

    task: str
    expected_result: str
    expected_tools: list[str] | None = None
    """Optional list of tool names that should be used to complete this task."""


@dataclass
class Scenario:
    """A scenario containing multiple tasks to be completed sequentially."""

    name: str
    tasks: list[Task]


@dataclass
class Personality:
    """A personality definition for the simulated user."""

    name: str
    description: str
