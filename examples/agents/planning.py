"""
Ragbits Agents Example: Planning Tools

This example demonstrates how to use planning tools with an agent.
The agent breaks down complex requests into tasks, works through them sequentially,
and builds context from completed tasks to generate comprehensive answers.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/planning.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents",
# ]
# ///
import asyncio

from pydantic import BaseModel

from ragbits.agents import Agent, AgentOptions, ToolCall, ToolCallResult
from ragbits.agents.tools.planning import PlanningState, create_planning_tools
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class CodePlannerInput(BaseModel):
    """
    Input format for the CodePlannerPrompt.
    """

    query: str


class CodePlannerPrompt(Prompt[CodePlannerInput, str]):
    """
    Prompt for a code planner agent.
    """

    system_prompt = """
    You are an expert software architect with planning capabilities.

    For complex design requests:
    1. Use `create_plan` to break down the architecture task into focused subtasks
    2. Work through each task using `get_current_task` and `complete_task`
    3. Keep working on tasks util there is nothing left
    4. Build on context from completed tasks

    Cover: technology stack, architecture patterns, scalability, and security.
    """
    user_prompt = "{{ query }}"


async def main() -> None:
    """
    Run the example.
    """
    planning_state = PlanningState()
    agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=CodePlannerPrompt,
        tools=create_planning_tools(planning_state),
        default_options=AgentOptions(max_turns=50),
    )
    query = (
        "Design a scalable e-commerce platform for 100k+ users with "
        "real-time inventory management and payment processing."
    )
    async for result in agent.run_streaming(CodePlannerInput(query=query)):
        match result:
            case str():
                print(result, end="", flush=True)
            case ToolCall():
                if result.arguments:
                    print(
                        f">>> TOOL CALL: {result.name}({', '.join(f'{k}={v!r}' for k, v in result.arguments.items())})"
                    )
                else:
                    print(f">>> TOOL CALL: {result.name}()")
            case ToolCallResult():
                print(f"<<< TOOL RESULT ({result.name}): {result.result}\n")


if __name__ == "__main__":
    asyncio.run(main())
