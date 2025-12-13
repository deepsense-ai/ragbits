"""Data models for agent simulation scenarios."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.display import ScenarioLiveDisplay
    from rich.console import Console


class Turn(BaseModel):
    """A single conversation turn between user and assistant."""

    user: str
    assistant: str


class Task(BaseModel):
    """A singular task or goal that simulated user is destined to complete."""

    task: str = Field(
        ...,
        description="A natural language description of the objective that simulated user needs to complete.",
    )
    expected_result: str = Field(
        ...,
        description="A description of desired outcome that indicates completness of simulated user objective.",
    )
    expected_tools: list[str] | None = Field(
        ...,
        description="Optional list of tool names that should be used to complete this task.",
    )


class Scenario(BaseModel):
    """A scenario containing multiple tasks to be completed sequentially."""

    name: str = Field(..., description="Short name identyfing the scenario")
    tasks: list[Task] = Field(
        default_factory=list,
        description=(
            "List of tasks that will be executed during the scenario. Simulating LLM will use this list to determine next steps. "
            "It can be both treated as conversation outline or a checklist that should be realized by simulated user. "
            "Expected result will be used to judge if specific exchange of messages was aligned with system expectactions. "
        ),
    )

    turn_limit: int | None = Field(
        None,
        description="Limit how many turns can be ran before failing the scenario. If set here it will override default settings.",
    )
    turn_limit_per_task: int | None = Field(
        None,
        description="Limit number of turns, this time per task. Specific tasks can override their limits.",
    )

    group: str | None = Field(
        None,
        description="Scenarios may be coupled together by being in the same group. Scenarios in groups are often executed one after another, may have some sort of dependencies or inference. In final results aggregated group metrics can be found.",
    )

    def display(self, console: Console | None = None) -> None:
        """Display scenario with rich panel."""
        from ragbits.evaluate.agent_simulation.display import display_scenario

        display_scenario(self, console)

    def live_display(self, console: Console | None = None) -> ScenarioLiveDisplay:
        """Create a live display for this scenario."""
        from ragbits.evaluate.agent_simulation.display import ScenarioLiveDisplay

        return ScenarioLiveDisplay(self, console)

    @classmethod
    def dto(cls) -> Type[Scenario]:
        if not hasattr(cls, "_dto_cls"):
            cls._dto_cls = create_model(
                "ScenarioDTO",
                __base__=cls,
                name=(str, cls.__pydantic_fields__["name"]),
                tasks=(list[Task], cls.__pydantic_fields__["tasks"]),
            )
        return cls._dto_cls


class Personality(BaseModel):
    """A personality definition for the simulated user."""

    name: str = Field(
        ...,
        description="A descriptive name that will help to identify this specific instance of personality.",
    )
    description: str = Field(
        ...,
        description="Detailed description of user behaviour, style of communication, internal motives, language, attitute, etc.",
    )
