"""Conversation orchestration for agent simulation scenarios."""

from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext
from ragbits.core.llms import Usage
from ragbits.evaluate.agent_simulation.deepeval_evaluator import DeepEvalEvaluator
from ragbits.evaluate.agent_simulation.logger import ConversationLogger
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Turn
from ragbits.evaluate.agent_simulation.simulation import GoalChecker, SimulatedUser, ToolUsageChecker, build_llm


def evaluate_with_deepeval(history: list[Turn], logger: ConversationLogger) -> None:
    """Evaluate conversation with DeepEval metrics.

    Args:
        history: List of conversation turns to evaluate
        logger: Logger instance to record evaluation results
    """
    if not history:
        return

    print("\n=== Running DeepEval Evaluation ===")
    deepeval_evaluator = DeepEvalEvaluator()
    try:
        evaluation_results = deepeval_evaluator.evaluate_conversation(history)
        logger.log_deepeval_metrics(evaluation_results)
        for metric_name, result in evaluation_results.items():
            score = result.get("score")
            if score is not None:
                print(f"{metric_name}: {score:.4f}")
            else:
                error = result.get("error", "Unknown error")
                print(f"{metric_name}: Error - {error}")
    except Exception as e:
        print(f"Error during DeepEval evaluation: {e}")
        logger.log_deepeval_metrics({"error": str(e)})


async def run_duet(  # noqa: PLR0912, PLR0915
    scenario: Scenario,
    chat: ChatInterface,
    max_turns: int = 10,  # max turns of the whole conversation, if needed could be changed to max turns per task
    log_file: str | None = None,
    agent_model_name: str | None = None,
    sim_user_model_name: str | None = None,
    checker_model_name: str | None = None,
    default_model: str = "gpt-4o-mini",
    api_key: str = "",
    user_message_prefix: str = "",
    personality: Personality | None = None,
) -> None:
    """Run a conversation between an agent and a simulated user.

    The conversation proceeds through tasks defined in the scenario, with a goal checker
    determining when each task is completed. The conversation is logged if a log file is provided.

    Args:
        scenario: The scenario containing tasks to complete
        agent: The agent to interact with
        chat: An instantiated ChatInterface used to drive the assistant side of the conversation.
        max_turns: Maximum number of conversation turns
        log_file: Optional path to log file
        agent_model_name: Optional override for agent LLM model name
        sim_user_model_name: Optional override for simulated user LLM model name
        checker_model_name: Optional override for goal checker LLM model name
        default_model: Default LLM model name
        api_key: API key for LLM
        user_message_prefix: Optional prefix to add to user messages before sending to agent
        personality: Optional personality to use for the simulated user
    """
    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(
        llm=build_llm(sim_user_model_name, default_model, api_key), scenario=scenario, personality=personality
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

    for turn_idx in range(1, max_turns + 1):
        current_task = sim_user.get_current_task()
        if current_task is None:
            print("\nAll tasks completed!")
            break

        print(f"\n=== Turn {turn_idx} ===")
        print(f"Current Task: {current_task.task}")
        print(f"User: {user_message}")

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
            f"Token usage: {turn_usage.total_tokens} total "
            f"({turn_usage.prompt_tokens} prompt + {turn_usage.completion_tokens} completion), "
            f"estimated cost: ${turn_usage.estimated_cost:.6f}"
        )
        logger.log_turn(turn_idx, current_task, user_message, assistant_reply, tool_calls, turn_usage)

        # Update simulation-visible history (Turn objects)
        history.append(Turn(user=user_message, assistant=assistant_reply))

        # Ask the judge if current task is achieved
        task_done, reason = await goal_checker.is_task_achieved(current_task, history)
        logger.log_task_check(turn_idx, task_done, reason)

        # Check tool usage if expected tools are specified
        if current_task.expected_tools:
            tools_used_correctly, tool_reason = tool_checker.check_tool_usage(current_task, tool_calls)
            logger.log_tool_check(turn_idx, tools_used_correctly, tool_reason, tool_calls)
            if not tools_used_correctly:
                print(f"Tool usage issue: {tool_reason}")
            else:
                print(f"Tool usage verified: {tool_reason}")
        if task_done:
            print(f"Task completed: {reason}")
            has_next = sim_user.advance_to_next_task()
            if not has_next:
                print("\nAll tasks completed!")
                break
            next_task = sim_user.get_current_task()
            if next_task:
                logger.log_task_transition(next_task)
        else:
            print(f"Task not completed: {reason}")
        # Ask the simulator for the next user message
        user_message = await sim_user.next_message(history)

    else:
        print("\nReached maximum number of turns. Exiting.")

    # Print total token usage summary
    print("\n=== Total Token Usage ===")
    print(
        f"Total tokens: {total_usage.total_tokens} "
        f"({total_usage.prompt_tokens} prompt + {total_usage.completion_tokens} completion)"
    )
    print(f"Total estimated cost: ${total_usage.estimated_cost:.6f}")
    logger.log_total_usage(total_usage)

    # Evaluate conversation with DeepEval metrics
    evaluate_with_deepeval(history, logger)

    logger.finalize_session()
