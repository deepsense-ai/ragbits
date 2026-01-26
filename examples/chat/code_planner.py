"""
Ragbits Chat Example: Code Planner

This example demonstrates how to use the ChatInterface with planning tools.

To run the script, execute the following command:

    ```bash
    uv run ragbits api run examples.chat.code_planner:CodePlannerChat
    ```
"""

from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.agents import Agent, AgentOptions, ToolCall, ToolCallResult
from ragbits.agents.tools.planning import PlanningState, create_planning_tools
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponseUnion, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import ChatFormat, Prompt


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


class CodePlannerChat(ChatInterface):
    """
    Code planner agent with planning capabilities.
    """

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Code Planner", subtitle="Spec driven development", logo="📋"),
        welcome_message="Code planner",
    )
    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.planning_state = PlanningState()
        self.agent = Agent(
            llm=LiteLLM("gpt-4.1-mini"),
            prompt=CodePlannerPrompt,
            tools=create_planning_tools(self.planning_state),
            default_options=AgentOptions(max_turns=50),
            keep_history=True,
        )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        """
        Chat implementation with planning capabilities.

        Args:
            message: The current user message.
            history: Previous messages in the conversation.
            context: Additional context for the chat.

        Yields:
            ChatResponse objects containing:
            - Text chunks for the response
            - Live updates showing planning progress
            - Todo items for plan tasks
        """
        async for response in self.agent.run_streaming(CodePlannerInput(query=message)):
            match response:
                case str():
                    yield self.create_text_response(response)

                case ToolCall():
                    if response.name == "create_plan":
                        yield self.create_live_update(
                            update_id=response.id,
                            type=LiveUpdateType.START,
                            label="Creating plan...",
                        )

                case ToolCallResult():
                    if self.planning_state.plan:
                        match response.name:
                            case "create_plan":
                                yield self.create_live_update(
                                    update_id=response.id,
                                    type=LiveUpdateType.FINISH,
                                    label="Plan created",
                                    description=f"{len(self.planning_state.plan.tasks)} tasks",
                                )
                                for task in self.planning_state.plan.tasks:
                                    yield self.create_todo_item_response(task)

                            case "get_current_task":
                                if self.planning_state.plan.current_task:
                                    yield self.create_live_update(
                                        update_id=self.planning_state.plan.current_task.id,
                                        type=LiveUpdateType.START,
                                        label=self.planning_state.plan.current_task.description,
                                    )
                                    yield self.create_todo_item_response(self.planning_state.plan.current_task)

                            case "complete_task":
                                if self.planning_state.plan.last_completed_task:
                                    yield self.create_live_update(
                                        update_id=self.planning_state.plan.last_completed_task.id,
                                        type=LiveUpdateType.FINISH,
                                        label=self.planning_state.plan.last_completed_task.description,
                                        description=self.planning_state.plan.last_completed_task.result,
                                    )
                                    yield self.create_todo_item_response(self.planning_state.plan.last_completed_task)
