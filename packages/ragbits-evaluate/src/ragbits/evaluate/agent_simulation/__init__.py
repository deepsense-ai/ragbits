"""Agent simulation utilities for evaluation scenarios.

This module uses lazy imports for components that require optional dependencies
(ragbits-agents, ragbits-chat) to allow importing result models independently.
"""

from typing import TYPE_CHECKING

# Import context, metrics, and result models eagerly - they have no external dependencies
from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext
from ragbits.evaluate.agent_simulation.metrics import (
    CompositeMetricCollector,
    LatencyMetricCollector,
    MetricCollector,
    TokenUsageMetricCollector,
    ToolUsageMetricCollector,
)
from ragbits.evaluate.agent_simulation.results import (
    ConversationMetrics,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.conversation import run_simulation
    from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator
    from ragbits.evaluate.agent_simulation.logger import ConversationLogger
    from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task, Turn
    from ragbits.evaluate.agent_simulation.scenarios import load_personalities, load_scenarios
    from ragbits.evaluate.agent_simulation.simulation import GoalChecker, SimulatedUser

__all__ = [
    "CompositeMetricCollector",
    "ConversationLogger",
    "ConversationMetrics",
    "DataSnapshot",
    "DeepEvalEvaluator",
    "DomainContext",
    "GoalChecker",
    "LatencyMetricCollector",
    "MetricCollector",
    "Personality",
    "Scenario",
    "SimulatedUser",
    "SimulationResult",
    "SimulationStatus",
    "Task",
    "TaskResult",
    "TokenUsageMetricCollector",
    "ToolUsageMetricCollector",
    "Turn",
    "TurnResult",
    "load_personalities",
    "load_scenarios",
    "run_simulation",
]


def __getattr__(name: str) -> object:
    """Lazy import for components with optional dependencies."""
    if name == "run_simulation":
        from ragbits.evaluate.agent_simulation.conversation import run_simulation

        return run_simulation
    if name == "DeepEvalEvaluator":
        from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator

        return DeepEvalEvaluator
    if name == "ConversationLogger":
        from ragbits.evaluate.agent_simulation.logger import ConversationLogger

        return ConversationLogger
    if name in ("Personality", "Scenario", "Task", "Turn"):
        from ragbits.evaluate.agent_simulation import models

        return getattr(models, name)
    if name in ("load_personalities", "load_scenarios"):
        from ragbits.evaluate.agent_simulation import scenarios

        return getattr(scenarios, name)
    if name in ("GoalChecker", "SimulatedUser"):
        from ragbits.evaluate.agent_simulation import simulation

        return getattr(simulation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
