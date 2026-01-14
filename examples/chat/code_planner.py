"""
Ragbits Chat Example: Code Planner

This example demonstrates how to use the ChatInterface to create a simple chat application with agent capabilities.
It showcases different response types, including text responses, live updates, and reference documents, as well as
the use of todo lists to help agents handle complex tasks.

To run the script, execute the following command:

    ```bash
    uv run ragbits api run examples.chat.code_planner:CodePlannerChat
    ```
"""

from collections.abc import AsyncGenerator

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import AgentRunContext
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tools.todo import ToDoPlanner
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import (
    ChatContext,
    ChatResponseUnion,
    ConfirmationRequestContent,
    ConfirmationRequestResponse,
    LiveUpdateType,
)
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import ChatFormat


def project_desctiption() -> None:
    """Get the project description."""



class CodePlannerChat(ChatInterface):
    """File explorer agent with confirmation for destructive actions."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="Code planner Agent", subtitle="secure file management with confirmation", logo="📂"
        ),
        welcome_message=(
            "Hello! I'm your file code planner.\n\n"
        ),
    )

    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

        # Define tools for the agent
        self.tools = [
            # no confirmation
            project_desctiption,
            # require confirmation
            self.planner
        ]
    async def planner(self, message: str, context: ChatContext) -> None:
        """Run the planner workflow for the given message."""
        print(f"message {message}")
        print(f"context {context}")
        print(f"self.conversation_history: {self.conversation_history}")
        llm = LiteLLM(model_name="gpt-4o-mini")
        todo_orchestrator = ToDoPlanner(agent_initial_prompt="""
            You are an expert hiking guide. Provide detailed, comprehensive information
            about hiking routes, gear, transportation, and safety considerations.
            """, llm=llm)
        async for response in todo_orchestrator.run_todo_workflow_streaming(message):
            print(response)

    async def chat(  # noqa: PLR0912
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        """
        Chat implementation with non-blocking confirmation support.

        The agent will check context.confirmed_tools for any confirmations.
        If a tool needs confirmation but hasn't been confirmed yet, it will
        yield a ConfirmationRequest and exit. The frontend will then send a
        new request with the confirmation in context.confirmed_tools.
        """
        # Create agent with history passed explicitly
        agent: Agent = Agent(
            llm=self.llm,
            prompt=f"""
            You are a code planner agent. You have tools available.

            CRITICAL: When a user asks you to perform an action, you MUST IMMEDIATELY CALL THE APPROPRIATE TOOL.
            DO NOT ask for permission in text - the system will automatically show a confirmation dialog.
            Describe what you would do in text.

            Example:
            User: "I would like to create project - one page site"
            CORRECT: Immediately call planner({ChatInterface})

            Available tools: {', '.join([t.__name__ for t in self.tools])}
            """,
            tools=self.tools,  # type: ignore[arg-type]
            history=history,
        )

        # Create agent context with confirmed_tools from the request context
        agent_context: AgentRunContext = AgentRunContext()

        # Pass confirmed_tools from ChatContext to AgentRunContext
        if context.confirmed_tools:
            agent_context.confirmed_tools = context.confirmed_tools

        # Run agent in streaming mode with the message and history
        async for response in agent.run_streaming(
            message,
            context=agent_context,
        ):
            # Pattern match on response types
            match response:
                case str():
                    # Regular text response
                    if response.strip():
                        yield self.create_text_response(response)

                case ToolCall():
                    print("ToolCall")
                    # Tool is being called
                    if response.type == "function":
                        print(agent.history)
                        print("type: function")
                        yield self.create_live_update(response.id, LiveUpdateType.START, f"🔧 {response.name}")

                    elif response.type == "planner":
                        print("type: planner")
                        yield self.create_text_response("Planning...")

                case ConfirmationRequest():
                    # Confirmation needed - send to frontend and wait for user response
                    yield ConfirmationRequestResponse(content=ConfirmationRequestContent(confirmation_request=response))

                case ToolCallResult():
                    # Tool execution completed (or pending confirmation)
                    result_preview = str(response.result)[:50]
                    yield self.create_live_update(
                        response.id, LiveUpdateType.FINISH, f"✅ {response.name}", result_preview
                    )

                # case Usage():
                #     # Usage information
                #     print(f"response: {response}")
                #     yield self.create_usage_response(response)
                # case TodoResult():

                #     if response.type == "task_list":
                #         print("task_list")
                #         # Display the task list to user
                #         task_display = "**Proposed Plan:**\n\n"
                #         for task in response.tasks:
                #             task_display += f"{task}\n\n"
                #         task_display += f"\n{response.message or ''}"
                #         yield self.create_text_response(task_display)
