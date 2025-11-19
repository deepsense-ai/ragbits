"""Data models for agent simulation scenarios."""

from __future__ import annotations

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


@dataclass
class Scenario:
    """A scenario containing multiple tasks to be completed sequentially."""

    name: str
    tasks: list[Task]
