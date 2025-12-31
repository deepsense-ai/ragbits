"""Conversation orchestration for agent simulation scenarios."""

from datetime import datetime, timezone

from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext
from ragbits.core.llms import Usage
from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext
from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator
from ragbits.evaluate.agent_simulation.logger import ConversationLogger
from ragbits.evaluate.agent_simulation.metrics.collectors import CompositeMetricCollector, MetricCollector
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Turn
from ragbits.evaluate.agent_simulation.results import (
    ConversationMetrics,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)
from ragbits.evaluate.agent_simulation.simulation import GoalChecker, SimulatedUser, ToolUsageChecker, build_llm


def _evaluate_with_deepeval(history: list[Turn], logger: ConversationLogger) -> dict[str, float]:
    """Evaluate conversation with DeepEval metrics.

    Args:
        history: List of conversation turns to evaluate
        logger: Logger instance to record evaluation results

    Returns:
        Dictionary of metric names to scores
    """
    scores: dict[str, float] = {}
    if not history:
        return scores

    print("\n=== Running DeepEval Evaluation ===")
    deepeval_evaluator = DeepEvalEvaluator()
    try:
        evaluation_results = deepeval_evaluator.evaluate_conversation(history)
        logger.log_deepeval_metrics(evaluation_results)
        for metric_name, result in evaluation_results.items():
            score = result.get("score")
            if score is not None:
                print(f"{metric_name}: {score:.4f}")
                scores[metric_name] = float(score)
            else:
                error = result.get("error", "Unknown error")
                print(f"{metric_name}: Error - {error}")
    except Exception as e:
        print(f"Error during DeepEval evaluation: {e}")
        logger.log_deepeval_metrics({"error": str(e)})

    return scores


async def run_simulation(  # noqa: PLR0912, PLR0915
    scenario: Scenario,
    chat: ChatInterface,
    max_turns_scenario: int = 15,
    max_turns_task: int | None = 4,
    log_file: str | None = None,
    agent_model_name: str | None = None,
    sim_user_model_name: str | None = None,
    checker_model_name: str | None = None,
    default_model: str = "gpt-4o-mini",
    api_key: str = "",
    user_message_prefix: str = "",
    personality: Personality | None = None,
    domain_context: DomainContext | None = None,
    data_snapshot: DataSnapshot | None = None,
    metric_collectors: list[MetricCollector] | None = None,
) -> SimulationResult:
    """Run a conversation between an agent and a simulated user.

    The conversation proceeds through tasks defined in the scenario, with a goal checker
    determining when each task is completed. Returns structured results for programmatic access.

    Args:
        scenario: The scenario containing tasks to complete
        chat: An instantiated ChatInterface used to drive the assistant side of the conversation.
        max_turns_scenario: Maximum number of conversation turns for the entire scenario
        max_turns_task: Maximum number of conversation turns per task (None for no limit)
        log_file: Optional path to log file
        agent_model_name: Optional override for agent LLM model name
        sim_user_model_name: Optional override for simulated user LLM model name
        checker_model_name: Optional override for goal checker LLM model name
        default_model: Default LLM model name
        api_key: API key for LLM
        user_message_prefix: Optional prefix to add to user messages before sending to agent
        personality: Optional personality to use for the simulated user
        domain_context: Optional domain context for goal checking (currency, locale, business rules)
        data_snapshot: Optional data snapshot to ground simulated user requests to available data
        metric_collectors: Optional list of custom metric collectors for per-turn metrics

    Returns:
        SimulationResult containing all turns, task results, and metrics
    """
    start_time = datetime.now(timezone.utc)

    # Initialize metric collectors
    collectors = CompositeMetricCollector(metric_collectors)

    # Initialize result tracking
    turn_results: list[TurnResult] = []
    task_results: list[TaskResult] = []
    task_turn_counts: dict[int, int] = {}  # task_index -> turns taken
    task_final_reasons: dict[int, str] = {}  # task_index -> final reason

    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(
        llm=build_llm(sim_user_model_name, default_model, api_key),
        scenario=scenario,
        personality=personality,
        data_snapshot=data_snapshot,
    )
    # Independent goal checker model
    goal_checker = GoalChecker(llm=build_llm(checker_model_name, default_model, api_key), scenario=scenario)
    # Tool usage checker (simple comparator, no LLM needed)
    tool_checker = ToolUsageChecker(scenario=scenario)

    history: list[Turn] = []
    logger = ConversationLogger(log_file)
    logger.initialize_session(scenario, agent_model_name, sim_user_model_name, checker_model_name, personality)
    total_usage = Usage()

    # Seed: ask the simulated user for the first message based on the first task
    user_message = await sim_user.next_message(history=history)

    turns_for_current_task = 0
    current_task_id = None
    status = SimulationStatus.RUNNING
    error_message: str | None = None

    try:
        for turn_idx in range(1, max_turns_scenario + 1):
            current_task = sim_user.get_current_task()
            if current_task is None:
                print("\nAll tasks completed!")
                status = SimulationStatus.COMPLETED
                break

            current_task_index = sim_user.current_task_idx

            # Track turns per task
            if current_task_id != id(current_task):
                # New task started, reset counter
                turns_for_current_task = 0
                current_task_id = id(current_task)

            # Check if we've exceeded max turns for this task
            if max_turns_task is not None and turns_for_current_task >= max_turns_task:
                print(f"\nReached maximum number of turns ({max_turns_task}) for current task. Exiting.")
                status = SimulationStatus.TIMEOUT
                task_final_reasons[current_task_index] = f"Timeout: exceeded {max_turns_task} turns"
                break

            turns_for_current_task += 1
            task_turn_counts[current_task_index] = task_turn_counts.get(current_task_index, 0) + 1

            print(f"\n=== Turn {turn_idx} (Task turn: {turns_for_current_task}) ===")
            print(f"Current Task: {current_task.task}")
            print(f"User: {user_message}")

            # Notify metric collectors of turn start
            collectors.on_turn_start(turn_idx, current_task_index, user_message)

            # Add optional prefix to user message
            full_user_message = user_message_prefix + user_message if user_message_prefix else user_message

            assistant_reply_parts: list[str] = []
            tool_calls: list[ToolCallResult] = []
            turn_usage: Usage = Usage()
            dummy_chat_context = ChatContext()

            stream = chat.chat(
                message=full_user_message,
                history=[
                    d
                    for turn in history
                    for d in ({"role": "user", "text": turn.user}, {"role": "assistant", "text": turn.assistant})
                ],
                context=dummy_chat_context,
            )

            async for chunk in stream:
                if isinstance(chunk, str):
                    assistant_reply_parts.append(chunk)
                elif isinstance(chunk, ToolCallResult):
                    tool_calls.append(chunk)
                elif isinstance(chunk, Usage):
                    turn_usage += chunk

            total_usage += turn_usage
            assistant_reply = "".join(assistant_reply_parts).strip()
            print(f"Assistant: {assistant_reply}")
            if tool_calls:
                print(f"Tools used: {[tc.name for tc in tool_calls]}")
            print(
                f"Assistant token usage: {turn_usage.total_tokens} total "
                f"({turn_usage.prompt_tokens} prompt + {turn_usage.completion_tokens} completion), "
                f"estimated cost: ${turn_usage.estimated_cost:.6f}"
            )
            logger.log_turn(turn_idx, current_task, user_message, assistant_reply, tool_calls, turn_usage)

            # Update simulation-visible history (Turn objects)
            history.append(Turn(user=user_message, assistant=assistant_reply))

            # Ask the judge if current task is achieved
            task_done, reason = await goal_checker.is_task_achieved(current_task, history, context=domain_context)
            logger.log_task_check(turn_idx, task_done, reason)

            # Check tool usage if expected tools are specified
            if current_task.expected_tools:
                tools_used_correctly, tool_reason = tool_checker.check_tool_usage(current_task, tool_calls)
                logger.log_tool_check(turn_idx, tools_used_correctly, tool_reason, tool_calls)
                if not tools_used_correctly:
                    print(f"Tool usage issue: {tool_reason}")
                else:
                    print(f"Tool usage verified: {tool_reason}")

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

            if task_done:
                print(f"Task completed: {reason}")
                task_final_reasons[current_task_index] = reason
                has_next = sim_user.advance_to_next_task()
                if not has_next:
                    print("\nAll tasks completed!")
                    status = SimulationStatus.COMPLETED
                    break
                next_task = sim_user.get_current_task()
                if next_task:
                    logger.log_task_transition(next_task)
                # Reset task turn counter when moving to next task
                turns_for_current_task = 0
                current_task_id = id(next_task) if next_task else None
            else:
                print(f"Task not completed: {reason}")
                task_final_reasons[current_task_index] = reason

            # Ask the simulator for the next user message
            user_message = await sim_user.next_message(history)

        else:
            print("\nReached maximum number of turns. Exiting.")
            status = SimulationStatus.TIMEOUT

    except Exception as e:
        status = SimulationStatus.FAILED
        error_message = str(e)
        print(f"\nSimulation failed with error: {error_message}")

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
    print("\n=== Total Assistant Token Usage ===")
    print(
        f"Total assistant tokens: {total_usage.total_tokens} "
        f"({total_usage.prompt_tokens} prompt + {total_usage.completion_tokens} completion)"
    )
    print(f"Total estimated cost: ${total_usage.estimated_cost:.6f}")
    logger.log_total_usage(total_usage)

    # Evaluate conversation with DeepEval metrics
    deepeval_scores = _evaluate_with_deepeval(history, logger)

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
        agent_model=agent_model_name,
        simulated_user_model=sim_user_model_name,
        checker_model=checker_model_name,
        personality=personality.name if personality else None,
        error=error_message,
        turns=turn_results,
        tasks=task_results,
        metrics=metrics,
    )
