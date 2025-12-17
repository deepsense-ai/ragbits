"""Conversation orchestration for agent simulation scenarios."""

import sys
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import IO, TYPE_CHECKING, Any

from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ConversationIdResponse, TextResponse
from ragbits.core.llms import Usage
from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator
from ragbits.evaluate.agent_simulation.logger import ConversationLogger
from ragbits.evaluate.agent_simulation.metrics.collectors import CompositeMetricCollector
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, SimulationConfig, Turn
from ragbits.evaluate.agent_simulation.results import (
    ConversationMetrics,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)
from ragbits.evaluate.agent_simulation.simulation import GoalChecker, SimulatedUser, ToolUsageChecker, build_llm

if TYPE_CHECKING:
    pass

ProgressCallback = Callable[[str, Any], Awaitable[None]]


def _serialize_response_chunk(chunk: Any) -> tuple[str, dict[str, Any]]:
    """Serialize a response chunk to (type, data) tuple.

    Args:
        chunk: The chunk to serialize (TextResponse, ToolCallResult, Usage, etc.)

    Returns:
        Tuple of (chunk_type, chunk_data_dict)
    """
    if isinstance(chunk, TextResponse):
        return ("text", {"text": chunk.content.text})
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
        # Fallback for unknown types
        return ("unknown", {"raw": str(chunk), "type": type(chunk).__name__})


def _evaluate_with_deepeval(
    history: list[Turn],
    logger: ConversationLogger,
    output_stream: IO[str] | None = None,
) -> dict[str, float]:
    """Evaluate conversation with DeepEval metrics.

    Args:
        history: List of conversation turns to evaluate
        logger: Logger instance to record evaluation results
        output_stream: Optional stream for output (defaults to sys.stdout)

    Returns:
        Dictionary of metric names to scores
    """
    out = output_stream if output_stream is not None else sys.stdout
    scores: dict[str, float] = {}
    if not history:
        return scores

    print("\n=== Running DeepEval Evaluation ===", file=out)
    deepeval_evaluator = DeepEvalEvaluator()
    try:
        evaluation_results = deepeval_evaluator.evaluate_conversation(history)
        logger.log_deepeval_metrics(evaluation_results)
        for metric_name, result in evaluation_results.items():
            score = result.get("score")
            if score is not None:
                print(f"{metric_name}: {score:.4f}", file=out)
                scores[metric_name] = float(score)
            else:
                error = result.get("error", "Unknown error")
                print(f"{metric_name}: Error - {error}", file=out)
    except Exception as e:
        print(f"Error during DeepEval evaluation: {e}", file=out)
        logger.log_deepeval_metrics({"error": str(e)})

    return scores


async def run_simulation(  # noqa: PLR0912, PLR0915
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
    # Use default config if not provided
    if config is None:
        config = SimulationConfig()

    # Use provided stream or default to stdout
    out = output_stream if output_stream is not None else sys.stdout
    start_time = datetime.now(timezone.utc)

    # Initialize metric collectors
    collectors = CompositeMetricCollector(config.metric_collectors)

    # Initialize result tracking
    turn_results: list[TurnResult] = []
    task_results: list[TaskResult] = []
    task_turn_counts: dict[int, int] = {}  # task_index -> turns taken
    task_final_reasons: dict[int, str] = {}  # task_index -> final reason

    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(
        llm=build_llm(config.sim_user_model_name, config.default_model, config.api_key),
        scenario=scenario,
        personality=personality,
        data_snapshot=config.data_snapshot,
    )
    # Independent goal checker model
    goal_checker = GoalChecker(
        llm=build_llm(config.checker_model_name, config.default_model, config.api_key), scenario=scenario
    )
    # Tool usage checker (simple comparator, no LLM needed)
    tool_checker = ToolUsageChecker(scenario=scenario)

    history: list[Turn] = []
    logger = ConversationLogger(config.log_file)
    logger.initialize_session(
        scenario, config.agent_model_name, config.sim_user_model_name, config.checker_model_name, personality
    )
    total_usage = Usage()

    # Seed: ask the simulated user for the first message based on the first task
    user_message = await sim_user.next_message(history=history)

    turns_for_current_task = 0
    current_task_id = None
    chat_context = ChatContext()
    status = SimulationStatus.RUNNING
    error_message: str | None = None

    try:
        for turn_idx in range(1, config.max_turns_scenario + 1):
            current_task = sim_user.get_current_task()
            if current_task is None:
                print("\nAll tasks completed!", file=out)
                status = SimulationStatus.COMPLETED
                break

            current_task_index = sim_user.current_task_idx

            # Track turns per task
            if current_task_id != id(current_task):
                # New task started, reset counter
                turns_for_current_task = 0
                current_task_id = id(current_task)

            # Check if we've exceeded max turns for this task
            if config.max_turns_task is not None and turns_for_current_task >= config.max_turns_task:
                print(
                    f"\nReached maximum number of turns ({config.max_turns_task}) for current task. Exiting.", file=out
                )
                status = SimulationStatus.TIMEOUT
                task_final_reasons[current_task_index] = f"Timeout: exceeded {config.max_turns_task} turns"
                break

            turns_for_current_task += 1
            task_turn_counts[current_task_index] = task_turn_counts.get(current_task_index, 0) + 1

            print(f"\n=== Turn {turn_idx} (Task turn: {turns_for_current_task}) ===", file=out)
            print(f"Current Task: {current_task.task}", file=out)
            print(f"User: {user_message}", file=out)

            # Notify metric collectors of turn start
            collectors.on_turn_start(turn_idx, current_task_index, user_message)

            # Add optional prefix to user message
            full_user_message = (
                config.user_message_prefix + user_message if config.user_message_prefix else user_message
            )

            assistant_reply_parts: list[str] = []
            tool_calls: list[ToolCallResult] = []
            turn_usage: Usage = Usage()

            stream = chat.chat(
                message=full_user_message,
                history=[
                    d
                    for turn in history
                    for d in ({"role": "user", "text": turn.user}, {"role": "assistant", "text": turn.assistant})
                ],
                context=chat_context,
            )

            async for chunk in stream:
                # Emit response chunk event for real-time streaming
                if progress_callback:
                    chunk_type, chunk_data = _serialize_response_chunk(chunk)
                    await progress_callback(
                        "response_chunk",
                        turn_index=turn_idx,
                        task_index=current_task_index,
                        chunk_type=chunk_type,
                        chunk_data=chunk_data,
                    )

                # Process chunk by type
                if isinstance(chunk, TextResponse):
                    assistant_reply_parts.append(chunk.content.text)
                elif isinstance(chunk, ToolCallResult):
                    tool_calls.append(chunk)
                elif isinstance(chunk, Usage):
                    turn_usage += chunk
                elif isinstance(chunk, ConversationIdResponse):
                    chat_context.conversation_id = chunk.content.conversation_id

            total_usage += turn_usage
            assistant_reply = "".join(assistant_reply_parts).strip()
            print(f"Assistant: {assistant_reply}", file=out)
            if tool_calls:
                print(f"Tools used: {[tc.name for tc in tool_calls]}", file=out)
            print(
                f"Assistant token usage: {turn_usage.total_tokens} total "
                f"({turn_usage.prompt_tokens} prompt + {turn_usage.completion_tokens} completion), "
                f"estimated cost: ${turn_usage.estimated_cost:.6f}",
                file=out,
            )
            logger.log_turn(turn_idx, current_task, user_message, assistant_reply, tool_calls, turn_usage)

            # Update simulation-visible history (Turn objects)
            history.append(Turn(user=user_message, assistant=assistant_reply))

            # Ask the judge if current task is achieved
            task_done, reason = await goal_checker.is_task_achieved(
                current_task, history, context=config.domain_context
            )
            logger.log_task_check(turn_idx, task_done, reason)

            # Check tool usage if expected tools are specified
            if current_task.expected_tools:
                tools_used_correctly, tool_reason = tool_checker.check_tool_usage(current_task, tool_calls)
                logger.log_tool_check(turn_idx, tools_used_correctly, tool_reason, tool_calls)
                if not tools_used_correctly:
                    print(f"Tool usage issue: {tool_reason}", file=out)
                else:
                    print(f"Tool usage verified: {tool_reason}", file=out)

            # Create turn result
            turn_result = TurnResult(
                turn_index=turn_idx,
                task_index=current_task_index,
                user_message=user_message,
                assistant_message=assistant_reply,
                tool_calls=[{"name": tc.name, "arguments": tc.arguments, "result": tc.result} for tc in tool_calls],
                task_completed=task_done,
                task_completed_reason=reason,
                token_usage={
                    "total": turn_usage.total_tokens,
                    "prompt": turn_usage.prompt_tokens,
                    "completion": turn_usage.completion_tokens,
                },
            )
            turn_results.append(turn_result)

            # Notify metric collectors of turn end
            collectors.on_turn_end(turn_result)

            # Emit progress callback for turn completion
            if progress_callback:
                await progress_callback(
                    "turn",
                    turn_index=turn_idx,
                    task_index=current_task_index,
                    user_message=user_message,
                    assistant_message=assistant_reply,
                    tool_calls=[{"name": tc.name, "arguments": tc.arguments, "result": tc.result} for tc in tool_calls],
                    task_completed=task_done,
                    task_completed_reason=reason,
                )

            if task_done:
                print(f"Task completed: {reason}", file=out)
                task_final_reasons[current_task_index] = reason

                # Emit progress callback for task completion
                if progress_callback:
                    await progress_callback(
                        "task_complete",
                        task_index=current_task_index,
                        task_description=current_task.task,
                        turns_taken=task_turn_counts.get(current_task_index, 0),
                        reason=reason,
                    )

                has_next = sim_user.advance_to_next_task()
                if not has_next:
                    print("\nAll tasks completed!", file=out)
                    status = SimulationStatus.COMPLETED
                    break
                next_task = sim_user.get_current_task()
                if next_task:
                    logger.log_task_transition(next_task)
                # Reset task turn counter when moving to next task
                turns_for_current_task = 0
                current_task_id = id(next_task) if next_task else None
            else:
                print(f"Task not completed: {reason}", file=out)
                task_final_reasons[current_task_index] = reason

            # Ask the simulator for the next user message
            user_message = await sim_user.next_message(history)

        else:
            print("\nReached maximum number of turns. Exiting.", file=out)
            status = SimulationStatus.TIMEOUT

    except Exception as e:
        status = SimulationStatus.FAILED
        error_message = str(e)
        print(f"\nSimulation failed with error: {error_message}", file=out)

    # Build task results
    for i, task in enumerate(scenario.tasks):
        completed = i < sim_user.current_task_idx or (
            i == sim_user.current_task_idx and status == SimulationStatus.COMPLETED
        )
        task_results.append(
            TaskResult(
                task_index=i,
                description=task.task,
                expected_result=task.expected_result,
                completed=completed,
                turns_taken=task_turn_counts.get(i, 0),
                final_reason=task_final_reasons.get(i, "Not attempted"),
            )
        )

    # Print total token usage summary
    print("\n=== Total Assistant Token Usage ===", file=out)
    print(
        f"Total assistant tokens: {total_usage.total_tokens} "
        f"({total_usage.prompt_tokens} prompt + {total_usage.completion_tokens} completion)",
        file=out,
    )
    print(f"Total estimated cost: ${total_usage.estimated_cost:.6f}", file=out)
    logger.log_total_usage(total_usage)

    # Evaluate conversation with DeepEval metrics
    deepeval_scores = _evaluate_with_deepeval(history, logger, output_stream=out)

    # Collect custom metrics from collectors
    custom_metrics = collectors.on_conversation_end(turn_results)

    logger.finalize_session()

    # Build metrics
    tasks_completed = sum(1 for t in task_results if t.completed)
    metrics = ConversationMetrics(
        total_turns=len(turn_results),
        total_tasks=len(scenario.tasks),
        tasks_completed=tasks_completed,
        total_tokens=total_usage.total_tokens,
        prompt_tokens=total_usage.prompt_tokens,
        completion_tokens=total_usage.completion_tokens,
        total_cost_usd=total_usage.estimated_cost,
        deepeval_scores=deepeval_scores,
        custom=custom_metrics,
    )

    return SimulationResult(
        scenario_name=scenario.name,
        start_time=start_time,
        end_time=datetime.now(timezone.utc),
        status=status,
        agent_model=config.agent_model_name,
        simulated_user_model=config.sim_user_model_name,
        checker_model=config.checker_model_name,
        personality=personality.name if personality else None,
        error=error_message,
        turns=turn_results,
        tasks=task_results,
        metrics=metrics,
    )
