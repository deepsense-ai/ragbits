"""Conversation orchestration for agent simulation scenarios."""

import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import IO, Any
from uuid import uuid4

from loguru import logger

from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import (
    ChatContext,
    ChatResponse,
    ConversationIdResponse,
    StateUpdateResponse,
    TextResponse,
)
from ragbits.core.llms import Usage
from ragbits.evaluate.agent_simulation.checkers import CheckerContext, CheckerResult, run_checkers
from ragbits.evaluate.agent_simulation.logger import ConversationLogger
from ragbits.evaluate.agent_simulation.metrics.builtin import (
    LatencyMetricCollector,
    TokenUsageMetricCollector,
    ToolUsageMetricCollector,
)
from ragbits.evaluate.agent_simulation.metrics.collectors import CompositeMetricCollector
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, SimulationConfig, Task, Turn
from ragbits.evaluate.agent_simulation.results import (
    CheckerResultItem,
    ConversationMetrics,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)
from ragbits.evaluate.agent_simulation.simulation import SimulatedUser, build_llm
from ragbits.evaluate.agent_simulation.tracing import MemoryTraceHandler, TraceAnalyzer, collect_traces

ProgressCallback = Callable[[str, Any], Awaitable[None]]


def _serialize_response_chunk(chunk: ChatResponse | ToolCallResult | Usage | object) -> tuple[str, dict[str, Any]]:
    """Serialize a response chunk to (type, data) tuple.

    Args:
        chunk: The chunk to serialize (TextResponse, ToolCallResult, Usage, etc.)

    Returns:
        Tuple of (chunk_type, chunk_data_dict)
    """
    if isinstance(chunk, ChatResponse):
        return (chunk.get_type(), chunk.content.model_dump())
    elif isinstance(chunk, ToolCallResult):
        return (
            "tool_call",
            {
                "name": chunk.name,
                "arguments": chunk.arguments,
                "result": chunk.result,
            },
        )
    elif isinstance(chunk, Usage):
        return (
            "usage",
            {
                "prompt_tokens": chunk.prompt_tokens,
                "completion_tokens": chunk.completion_tokens,
                "total_tokens": chunk.total_tokens,
                "estimated_cost": chunk.estimated_cost,
                "n_requests": chunk.n_requests,
            },
        )
    else:
        return ("unknown", {"raw": str(chunk), "type": type(chunk).__name__})


def _build_checker_results(checker_result: CheckerResult) -> tuple[list[CheckerResultItem], str]:
    """Build checker result items from a CheckerResult.

    Args:
        checker_result: The result from running checkers

    Returns:
        Tuple of (list of CheckerResultItem, checker_mode)
    """
    checkers_list: list[CheckerResultItem] = []
    all_results = checker_result.details.get("all_results", [])
    checker_mode = checker_result.details.get("mode", "all")

    if all_results:
        for r in all_results:
            checkers_list.append(
                CheckerResultItem(
                    type=r.get("checker_type", "unknown"),
                    completed=r.get("completed", False),
                    reason=r.get("reason", ""),
                )
            )
    else:
        checkers_list.append(
            CheckerResultItem(
                type=checker_result.checker_type,
                completed=checker_result.completed,
                reason=checker_result.reason,
            )
        )

    return checkers_list, checker_mode


@dataclass
class TurnData:
    """Data collected during a single turn."""

    usage: Usage
    user_message: str
    assistant_response: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)


@dataclass
class TaskData:
    """Data collected for a single task."""

    task_index: int
    turns: list[TurnData] = field(default_factory=list)
    final_reason: str = ""
    completed: bool = False


@dataclass
class SimulationState:
    """Mutable state tracking during simulation execution."""

    simulation_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_task_idx: int = 0
    current_turn_idx: int = 0
    turns_for_current_task: int = 0
    current_task_id: int | None = None

    # Accumulated results
    turn_results: list[TurnResult] = field(default_factory=list)
    task_data: dict[int, TaskData] = field(default_factory=dict)
    history: list[Turn] = field(default_factory=list)
    total_usage: Usage = field(default_factory=Usage)

    # Context
    chat_context: ChatContext = field(default_factory=ChatContext)
    status: SimulationStatus = SimulationStatus.RUNNING
    error_message: str | None = None

    # Cache
    task_checkers_cache: dict[int, list] = field(default_factory=dict)

    def get_task_turn_count(self, task_index: int) -> int:
        """Get the number of turns taken for a task."""
        if task_index in self.task_data:
            return len(self.task_data[task_index].turns)
        return 0

    def get_task_final_reason(self, task_index: int) -> str:
        """Get the final reason for a task."""
        if task_index in self.task_data:
            return self.task_data[task_index].final_reason
        return "Not attempted"

    def ensure_task_data(self, task_index: int) -> TaskData:
        """Ensure task data exists for the given index."""
        if task_index not in self.task_data:
            self.task_data[task_index] = TaskData(task_index=task_index)
        return self.task_data[task_index]

    def record_turn(
        self,
        task_index: int,
        user_message: str,
        assistant_response: str,
        usage: Usage,
        tool_calls: list[ToolCallResult],
    ) -> None:
        """Record turn data for the current task."""
        task_data = self.ensure_task_data(task_index)
        task_data.turns.append(
            TurnData(
                usage=usage,
                user_message=user_message,
                assistant_response=assistant_response,
                tool_calls=tool_calls,
            )
        )

    def set_task_result(self, task_index: int, completed: bool, reason: str) -> None:
        """Set the result for a task."""
        task_data = self.ensure_task_data(task_index)
        task_data.completed = completed
        task_data.final_reason = reason

    def on_new_task(self, task_id: int) -> None:
        """Handle transition to a new task."""
        self.turns_for_current_task = 0
        self.current_task_id = task_id


@dataclass
class SimulationContext:
    """Environment and dependencies for running a simulation."""

    config: SimulationConfig
    chat: ChatInterface
    sim_user: SimulatedUser
    checker_context: CheckerContext
    logger: ConversationLogger
    collectors: CompositeMetricCollector
    out: IO[str]
    trace_handler: MemoryTraceHandler | None = None
    progress_callback: ProgressCallback | None = None

    async def emit_progress(self, event_type: str, **kwargs: Any) -> None:
        """Emit a progress callback if one is configured."""
        if self.progress_callback:
            await self.progress_callback(event_type, **kwargs)

    def print(self, message: str) -> None:
        """Print a message to the output stream."""
        print(message, file=self.out)


async def _process_chat_stream(
    ctx: SimulationContext,
    state: SimulationState,
    turn_idx: int,
    task_index: int,
    full_user_message: str,
    user_message: str,
) -> tuple[str, list[ToolCallResult], Usage]:
    """Process the chat stream and collect response data.

    Tool calls and usage are extracted from traces rather than from the stream,
    providing more reliable and complete data.

    Returns:
        Tuple of (assistant_reply, tool_calls, turn_usage)
    """
    assistant_reply_parts: list[str] = []

    # Track span count before the stream to identify new spans from this turn
    span_count_before = len(ctx.trace_handler.root_spans) if ctx.trace_handler else 0

    stream = ctx.chat.chat(
        message=full_user_message,
        history=[
            d
            for turn in state.history
            for d in ({"role": "user", "text": turn.user}, {"role": "assistant", "text": turn.assistant})
        ],
        context=state.chat_context,
    )

    async for chunk in stream:
        # Emit response chunk event for real-time streaming
        if ctx.progress_callback:
            chunk_type, chunk_data = _serialize_response_chunk(chunk)
            await ctx.emit_progress(
                "response_chunk",
                turn_index=turn_idx,
                task_index=task_index,
                chunk_type=chunk_type,
                chunk_data=chunk_data,
            )

        ctx.collectors.on_streamed_response(turn_idx, task_index, user_message, chunk)

        # Process chunk by type - only collect text and context updates from stream
        if isinstance(chunk, TextResponse):
            assistant_reply_parts.append(chunk.content.text)
        elif isinstance(chunk, ConversationIdResponse):
            state.chat_context.conversation_id = chunk.content.conversation_id
        elif isinstance(chunk, StateUpdateResponse):
            state.chat_context.state = chunk.content.state

    # Extract tool calls and usage from traces for this turn
    tool_calls: list[ToolCallResult] = []
    turn_usage = Usage()

    if ctx.trace_handler:
        # Get only the new spans from this turn
        new_spans = ctx.trace_handler.root_spans[span_count_before:]
        if new_spans:
            # Create analyzer from just this turn's spans
            turn_traces = [span.to_dict() for span in new_spans]
            analyzer = TraceAnalyzer.from_traces(turn_traces)
            tool_calls = analyzer.get_tool_calls()
            turn_usage = analyzer.get_usage()

    return "".join(assistant_reply_parts).strip(), tool_calls, turn_usage


def _build_simulation_result(
    scenario: Scenario,
    ctx: SimulationContext,
    state: SimulationState,
    task_results: list[TaskResult],
    collector_metrics: dict[str, Any],
    personality: Personality | None,
    traces: list[dict[str, Any]],
) -> SimulationResult:
    """Build the final SimulationResult from state and metrics."""
    tasks_completed = sum(1 for t in task_results if t.completed)
    total_tasks = len(scenario.tasks)

    metrics_dict: dict[str, Any] = {
        "total_turns": len(state.turn_results),
        "total_tasks": total_tasks,
        "tasks_completed": tasks_completed,
        "success_rate": tasks_completed / total_tasks if total_tasks > 0 else 0.0,
    }
    metrics_dict.update(collector_metrics)

    return SimulationResult(
        scenario_name=scenario.name,
        start_time=state.start_time,
        end_time=datetime.now(timezone.utc),
        status=state.status,
        agent_model=ctx.config.agent_model_name,
        simulated_user_model=ctx.config.sim_user_model_name,
        checker_model=ctx.config.checker_model_name,
        persona=personality.name if personality else None,
        error=state.error_message,
        conversation_id=state.chat_context.conversation_id,
        final_state=state.chat_context.state,
        turns=state.turn_results,
        tasks=task_results,
        metrics=ConversationMetrics(metrics=metrics_dict),
        traces=traces,
    )


def _build_task_results(
    scenario: Scenario,
    ctx: SimulationContext,
    state: SimulationState,
) -> list[TaskResult]:
    """Build task results from scenario and state."""
    task_results: list[TaskResult] = []
    for i, task in enumerate(scenario.tasks):
        completed = i < ctx.sim_user.current_task_idx or (
            i == ctx.sim_user.current_task_idx and state.status == SimulationStatus.COMPLETED
        )
        task_results.append(
            TaskResult(
                task_index=i,
                description=task.task,
                completed=completed,
                turns_taken=state.get_task_turn_count(i),
                final_reason=state.get_task_final_reason(i),
                checkers=task.checkers,
                checker_mode=task.checker_mode,
            )
        )
    return task_results


async def _handle_task_completion(
    ctx: SimulationContext,
    state: SimulationState,
    current_task_index: int,
    current_task: Task,
    reason: str,
) -> bool:
    """Handle task completion. Returns True if simulation should continue."""
    ctx.print(f"Task completed: {reason}")
    state.set_task_result(current_task_index, True, reason)

    await ctx.emit_progress(
        "task_complete",
        task_index=current_task_index,
        task_description=current_task.task,
        turns_taken=state.get_task_turn_count(current_task_index),
        reason=reason,
    )

    has_next = ctx.sim_user.advance_to_next_task()
    if not has_next:
        ctx.print("\nAll tasks completed!")
        state.status = SimulationStatus.COMPLETED
        return False

    next_task = ctx.sim_user.get_current_task()
    if next_task:
        ctx.logger.log_task_transition(next_task)
    state.on_new_task(id(next_task) if next_task else None)
    return True


async def _run_turn_checkers(
    ctx: SimulationContext,
    state: SimulationState,
    current_task: Task,
    current_task_index: int,
    tool_calls: list[ToolCallResult],
) -> CheckerResult:
    """Run checkers for the current turn and return the result."""
    if current_task_index not in state.task_checkers_cache:
        state.task_checkers_cache[current_task_index] = current_task.get_parsed_checkers()

    return await run_checkers(
        checkers=state.task_checkers_cache[current_task_index],
        task=current_task,
        history=state.history,
        tool_calls=tool_calls,
        state=state.chat_context.state,
        context=ctx.checker_context,
        mode=current_task.checker_mode,
    )


async def _emit_turn_progress(
    ctx: SimulationContext,
    turn_idx: int,
    current_task_index: int,
    current_task: Task,
    user_message: str,
    assistant_reply: str,
    tool_calls_data: list[dict[str, Any]],
    checker_result: CheckerResult,
    checkers_list: list[CheckerResultItem],
    checker_mode: str,
) -> None:
    """Emit progress events for checker decision and turn completion."""
    task_done = checker_result.completed
    reason = checker_result.reason

    await ctx.emit_progress(
        "response_chunk",
        turn_index=turn_idx,
        task_index=current_task_index,
        chunk_type="checker_decision",
        chunk_data={
            "task_completed": task_done,
            "reason": reason,
            "task_description": current_task.task,
            "checkers": [c.to_dict() for c in checkers_list],
            "checker_mode": checker_mode,
        },
    )

    await ctx.emit_progress(
        "turn",
        turn_index=turn_idx,
        task_index=current_task_index,
        user_message=user_message,
        assistant_message=assistant_reply,
        tool_calls=tool_calls_data,
        task_completed=task_done,
        task_completed_reason=reason,
        checkers=[c.to_dict() for c in checkers_list],
        checker_mode=checker_mode,
    )


def _create_simulation_context(
    scenario: Scenario,
    chat: ChatInterface,
    config: SimulationConfig,
    personality: Personality | None,
    progress_callback: ProgressCallback | None,
    output_stream: IO[str] | None,
    trace_handler: MemoryTraceHandler | None = None,
) -> SimulationContext:
    """Create the simulation context with all dependencies."""
    out = output_stream if output_stream is not None else sys.stdout

    # Create metric collectors
    builtin_collectors = [
        LatencyMetricCollector(),
        TokenUsageMetricCollector(),
        ToolUsageMetricCollector(),
    ]
    user_collectors = config.create_metric_collectors()
    collectors = CompositeMetricCollector(builtin_collectors + user_collectors)

    # Simulated user
    sim_user = SimulatedUser(
        llm=build_llm(config.sim_user_model_name, config.default_model, config.api_key),
        scenario=scenario,
        personality=personality,
        data_snapshot=config.data_snapshot,
    )

    # Checker context
    checker_llm = build_llm(config.checker_model_name, config.default_model, config.api_key)
    checker_context = CheckerContext(llm=checker_llm, domain_context=config.domain_context)

    # Logger
    logger = ConversationLogger(config.log_file)
    logger.initialize_session(
        scenario, config.agent_model_name, config.sim_user_model_name, config.checker_model_name, personality
    )

    return SimulationContext(
        config=config,
        chat=chat,
        sim_user=sim_user,
        checker_context=checker_context,
        logger=logger,
        collectors=collectors,
        out=out,
        trace_handler=trace_handler,
        progress_callback=progress_callback,
    )


async def _execute_turn(
    ctx: SimulationContext,
    state: SimulationState,
    turn_idx: int,
    current_task: Task,
    current_task_index: int,
    user_message: str,
) -> tuple[bool, str]:
    """Execute a single turn. Returns (should_continue, next_user_message)."""
    ctx.print(f"\n=== Turn {turn_idx} (Task turn: {state.turns_for_current_task}) ===")
    ctx.print(f"Current Task: {current_task.task}")
    ctx.print(f"User: {user_message}")

    ctx.collectors.on_turn_start(turn_idx, current_task_index, user_message)

    full_user_message = (
        ctx.config.user_message_prefix + user_message if ctx.config.user_message_prefix else user_message
    )

    # Process assistant response
    assistant_reply, tool_calls, turn_usage = await _process_chat_stream(
        ctx, state, turn_idx, current_task_index, full_user_message, user_message
    )

    state.total_usage += turn_usage
    _log_turn_output(ctx, assistant_reply, tool_calls, turn_usage)
    ctx.logger.log_turn(turn_idx, current_task, user_message, assistant_reply, tool_calls, turn_usage)

    # Update state
    state.history.append(Turn(user=user_message, assistant=assistant_reply))
    state.record_turn(current_task_index, user_message, assistant_reply, turn_usage, tool_calls)

    # Run checkers
    checker_result = await _run_turn_checkers(ctx, state, current_task, current_task_index, tool_calls)
    ctx.logger.log_task_check(turn_idx, checker_result.completed, checker_result.reason)

    # Build and record turn result
    checkers_list, checker_mode = _build_checker_results(checker_result)
    tool_calls_data = [{"name": tc.name, "arguments": tc.arguments, "result": tc.result} for tc in tool_calls]

    turn_result = TurnResult(
        turn_index=turn_idx,
        task_index=current_task_index,
        user_message=user_message,
        assistant_message=assistant_reply,
        tool_calls=tool_calls_data,
        task_completed=checker_result.completed,
        task_completed_reason=checker_result.reason,
        token_usage=turn_usage,
        checkers=checkers_list,
        checker_mode=checker_mode,
    )
    state.turn_results.append(turn_result)
    ctx.collectors.on_turn_end(turn_result)

    # Emit progress
    await _emit_turn_progress(
        ctx,
        turn_idx,
        current_task_index,
        current_task,
        user_message,
        assistant_reply,
        tool_calls_data,
        checker_result,
        checkers_list,
        checker_mode,
    )

    status = "✓" if checker_result.completed else "✗"
    ctx.print(f"Checker [{checker_result.checker_type}]: {status} {checker_result.reason}")

    # Handle task completion or continuation
    if checker_result.completed:
        should_continue = await _handle_task_completion(
            ctx, state, current_task_index, current_task, checker_result.reason
        )
        if not should_continue:
            return False, ""
    else:
        ctx.print(f"Task not completed: {checker_result.reason}")
        state.set_task_result(current_task_index, False, checker_result.reason)

    next_message = await ctx.sim_user.next_message(state.history)
    return True, next_message


def _log_turn_output(
    ctx: SimulationContext,
    assistant_reply: str,
    tool_calls: list[ToolCallResult],
    turn_usage: Usage,
) -> None:
    """Log turn output to the output stream."""
    ctx.print(f"Assistant: {assistant_reply}")
    if tool_calls:
        ctx.print(f"Tools used: {[tc.name for tc in tool_calls]}")
    ctx.print(
        f"Assistant token usage: {turn_usage.total_tokens} total "
        f"({turn_usage.prompt_tokens} prompt + {turn_usage.completion_tokens} completion), "
        f"estimated cost: ${turn_usage.estimated_cost:.6f}"
    )


async def _run_simulation_loop(
    ctx: SimulationContext,
    state: SimulationState,
    user_message: str,
) -> None:
    """Run the main simulation loop."""
    for turn_idx in range(1, ctx.config.max_turns_scenario + 1):
        current_task = ctx.sim_user.get_current_task()
        if current_task is None:
            ctx.print("\nAll tasks completed!")
            state.status = SimulationStatus.COMPLETED
            return

        current_task_index = ctx.sim_user.current_task_idx

        if state.current_task_id != id(current_task):
            state.on_new_task(id(current_task))

        if ctx.config.max_turns_task is not None and state.turns_for_current_task >= ctx.config.max_turns_task:
            ctx.print(f"\nReached maximum number of turns ({ctx.config.max_turns_task}) for current task. Exiting.")
            state.status = SimulationStatus.TIMEOUT
            state.set_task_result(current_task_index, False, f"Timeout: exceeded {ctx.config.max_turns_task} turns")
            return

        state.turns_for_current_task += 1
        state.ensure_task_data(current_task_index)

        should_continue, user_message = await _execute_turn(
            ctx, state, turn_idx, current_task, current_task_index, user_message
        )
        if not should_continue:
            return

    ctx.print("\nReached maximum number of turns. Exiting.")
    state.status = SimulationStatus.TIMEOUT


async def run_simulation(
    scenario: Scenario,
    chat: ChatInterface,
    config: SimulationConfig | None = None,
    *,
    personality: Personality | None = None,
    progress_callback: ProgressCallback | None = None,
    output_stream: IO[str] | None = None,
) -> SimulationResult:
    """Run a conversation between an agent and a simulated user.

    The conversation proceeds through tasks defined in the scenario, with a goal checker
    determining when each task is completed. Returns structured results for programmatic access.

    Args:
        scenario: The scenario containing tasks to complete
        chat: An instantiated ChatInterface used to drive the assistant side of the conversation.
        config: Optional SimulationConfig with all simulation parameters. If not provided,
            uses default values.
        personality: Optional personality to use for the simulated user.
        progress_callback: Optional async callback for progress updates (event_type, **kwargs)
        output_stream: Optional stream for simulation output (print statements).
            If None, defaults to sys.stdout. Pass a file handle, StringIO,
            or any file-like object to redirect output. Use io.StringIO()
            to capture output or a custom stream to integrate with logging.

    Returns:
        SimulationResult containing all turns, task results, and metrics
    """
    if config is None:
        config = SimulationConfig()

    state = SimulationState()

    # Collect traces from all traceable operations during the simulation
    with collect_traces(simulation_id=state.simulation_id) as trace_handler:
        ctx = _create_simulation_context(
            scenario=scenario,
            chat=chat,
            config=config,
            personality=personality,
            progress_callback=progress_callback,
            output_stream=output_stream,
            trace_handler=trace_handler,
        )

        user_message = await ctx.sim_user.next_message(history=state.history)

        try:
            await _run_simulation_loop(ctx, state, user_message)
        except Exception as e:
            state.status = SimulationStatus.FAILED
            state.error_message = str(e)
            ctx.print(f"\nSimulation failed with error: {state.error_message}")

        traces = trace_handler.get_traces()
        logger.debug(traces)

    task_results = _build_task_results(scenario, ctx, state)
    ctx.logger.log_total_usage(state.total_usage)
    collector_metrics = ctx.collectors.on_conversation_end(state.turn_results)
    ctx.logger.finalize_session()

    return _build_simulation_result(scenario, ctx, state, task_results, collector_metrics, personality, traces)
