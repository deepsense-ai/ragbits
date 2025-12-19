"""Agent simulation utilities for evaluation scenarios.

This module uses lazy imports for components that require optional dependencies
(ragbits-agents, ragbits-chat) to allow importing result models independently.
"""

from typing import TYPE_CHECKING

from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext
from ragbits.evaluate.agent_simulation.metrics import (
    CompositeMetricCollector,
    DeepEvalAllMetricsCollector,
    DeepEvalCompletenessMetricCollector,
    DeepEvalKnowledgeRetentionMetricCollector,
    DeepEvalRelevancyMetricCollector,
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
    from ragbits.agents.tool import ToolCallResult
    from ragbits.core.llms.base import ToolCall, Usage, UsageItem
    from ragbits.evaluate.agent_simulation.conversation import run_simulation
    from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator
    from ragbits.evaluate.agent_simulation.logger import ConversationLogger
    from ragbits.evaluate.agent_simulation.models import Personality, Scenario, SimulationConfig, Task, Turn
    from ragbits.evaluate.agent_simulation.scenarios import load_personalities, load_scenarios
    from ragbits.evaluate.agent_simulation.simulation import GoalChecker, SimulatedUser
    from ragbits.evaluate.agent_simulation.tracing import (
        LLMCall,
        MemoryTraceHandler,
        TraceAnalyzer,
        TraceSpan,
        collect_traces,
    )

__all__ = [
    # Metrics
    "CompositeMetricCollector",
    # Components (lazy loaded)
    "ConversationLogger",
    # Results
    "ConversationMetrics",
    # Context
    "DataSnapshot",
    "DeepEvalAllMetricsCollector",
    "DeepEvalCompletenessMetricCollector",
    "DeepEvalEvaluator",
    "DeepEvalKnowledgeRetentionMetricCollector",
    "DeepEvalRelevancyMetricCollector",
    "DomainContext",
    "GoalChecker",
    # Tracing (lazy loaded)
    "LLMCall",
    "LatencyMetricCollector",
    "MemoryTraceHandler",
    "MetricCollector",
    "Personality",
    "Scenario",
    "SimulatedUser",
    "SimulationConfig",
    "SimulationResult",
    "SimulationStatus",
    "Task",
    "TaskResult",
    "TokenUsageMetricCollector",
    # Re-exports from ragbits-core/agents
    "ToolCall",
    "ToolCallResult",
    "ToolUsageMetricCollector",
    "TraceAnalyzer",
    "TraceSpan",
    "Turn",
    "TurnResult",
    "Usage",
    "UsageItem",
    "collect_traces",
    # Functions (lazy loaded)
    "load_personalities",
    "load_scenarios",
    "run_simulation",
]


def __getattr__(name: str) -> object:  # noqa: PLR0911
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
    if name in ("Personality", "Scenario", "SimulationConfig", "Task", "Turn"):
        from ragbits.evaluate.agent_simulation import models

        return getattr(models, name)
    if name in ("load_personalities", "load_scenarios"):
        from ragbits.evaluate.agent_simulation import scenarios

        return getattr(scenarios, name)
    if name in ("GoalChecker", "SimulatedUser"):
        from ragbits.evaluate.agent_simulation import simulation

        return getattr(simulation, name)
    if name in ("LLMCall", "MemoryTraceHandler", "TraceAnalyzer", "TraceSpan", "collect_traces"):
        from ragbits.evaluate.agent_simulation import tracing

        return getattr(tracing, name)
    if name in ("ToolCall", "Usage", "UsageItem"):
        from ragbits.core.llms import base

        return getattr(base, name)
    if name == "ToolCallResult":
        from ragbits.agents.tool import ToolCallResult

        return ToolCallResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
