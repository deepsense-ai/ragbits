"""Rich display components for agent simulation."""

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ragbits.evaluate.agent_simulation.models import Scenario


def display_scenario(scenario: Scenario, console: Console | None = None) -> None:
    """Display scenario with rich panel.

    Args:
        scenario: The scenario to display.
        console: Optional Rich console instance. If not provided, a new one is created.
    """
    if console is None:
        console = Console()

    console.print(_build_panel(scenario))


def _build_panel(
    scenario: Scenario,
    current_task_idx: int | None = None,
    task_status: dict[int, str] | None = None,
    metrics: dict[str, str | int | float] | None = None,
) -> Panel:
    """Build a rich panel for the scenario.

    Args:
        scenario: The scenario to display.
        current_task_idx: Index of currently running task (for live display).
        task_status: Dict mapping task index to status emoji/text.
        metrics: Optional metrics to display at the bottom.

    Returns:
        Rich Panel object.
    """
    lines = Text()

    for i, task in enumerate(scenario.tasks):
        # Status indicator
        if task_status and i in task_status:
            status = task_status[i]
        elif current_task_idx is not None and i == current_task_idx:
            status = "▶"
        elif current_task_idx is not None and i < current_task_idx:
            status = "✓"
        else:
            status = " "

        style = "bold" if current_task_idx == i else ""
        lines.append(f"{status} {i + 1}. {task.task}\n", style=style)
        lines.append(f"     → {task.expected_result}\n", style="green")
        if task.expected_tools:
            lines.append(f"     tools: {', '.join(task.expected_tools)}\n", style="dim")

    if metrics:
        lines.append("\n")
        for key, value in metrics.items():
            lines.append(f"{key}: {value}  ", style="cyan")

    title = scenario.name
    if scenario.group:
        title += f" [dim]({scenario.group})[/dim]"

    return Panel(lines, title=title, border_style="blue")


class ScenarioLiveDisplay:
    """Live display for scenario execution with real-time updates."""

    def __init__(self, scenario: Scenario, console: Console | None = None) -> None:
        self.scenario = scenario
        self.console = console or Console()
        self.current_task_idx: int | None = None
        self.task_status: dict[int, str] = {}
        self.metrics: dict[str, str | int | float] = {}
        self._live: Live | None = None

    def __enter__(self) -> "ScenarioLiveDisplay":
        self._live = Live(self._render(), console=self.console, refresh_per_second=4)
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        if self._live:
            self._live.__exit__(*args)

    def _render(self) -> Panel:
        return _build_panel(
            self.scenario,
            current_task_idx=self.current_task_idx,
            task_status=self.task_status,
            metrics=self.metrics,
        )

    def update(self) -> None:
        """Refresh the display."""
        if self._live:
            self._live.update(self._render())

    def set_current_task(self, idx: int) -> None:
        """Set the currently running task index."""
        self.current_task_idx = idx
        self.update()

    def mark_task_done(self, idx: int, success: bool = True) -> None:
        """Mark a task as completed."""
        self.task_status[idx] = "✓" if success else "✗"
        self.update()

    def set_metric(self, key: str, value: str | int | float) -> None:
        """Update a metric value."""
        self.metrics[key] = value
        self.update()
