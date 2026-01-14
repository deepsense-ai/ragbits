"""
Ragbits Chat Example: Chat Interface

This example demonstrates how to use the ChatInterface to create a simple chat application with agent capabilities.
It showcases different response types, including text responses, live updates, and reference documents, as well as
the use of todo lists to help agents handle complex tasks.

To run the script, execute the following command:

    ```bash
    ragbits api run examples.chat.hiking_agent:MyChat
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-agents",
#     "ragbits-chat",
# ]
# ///
#

from collections.abc import AsyncGenerator

from ragbits.agents.tools.todo import ToDoPlanner, TodoResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponseUnion, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, PageMetaCustomization, UICustomization
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import ChatFormat


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Example Ragbits Agent Chat", subtitle="by deepsense.ai", logo="🐰"),
        welcome_message=(
            "Hello! I'm your AI hiking trip assistant.\n\n How can I help you today? "
            "You can ask me **anything**! "
            "I can provide information, answer questions, and assist you with various tasks."
        ),
        meta=PageMetaCustomization(favicon="🔨", page_title="Change me!"),
    )

    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")
        self.todo_orchestrator = ToDoPlanner(
            agent_initial_prompt="""
            You are an expert hiking guide. Provide detailed, comprehensive information
            about hiking routes, gear, transportation, and safety considerations.
            """,
            llm=self.llm,
        )
        # self.agent = Agent(
        #     llm=self.llm,
        #     prompt=,
        # )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        """
        Example implementation of the ChatInterface.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Reference documents used to generate the response
        """
        live_update_counter = 0

        async for response in self.todo_orchestrator.run_todo_workflow_streaming(message):
            match response:
                case str():
                    yield self.create_text_response(response)
                case TodoResult():
                    if response.type in ("status"):
                        yield self.create_live_update(
                            str(live_update_counter), LiveUpdateType.FINISH, response.message or ""
                        )
                        live_update_counter += 1

                    elif response.type in ("task_list"):
                        for task in response.tasks:
                            yield self.create_todo_item_response(task)
                        yield self.create_followup_messages(self.todo_orchestrator.task_feedback_options)

                    elif response.type in ("start_task"):
                        if response.current_task is not None:
                            yield self.create_todo_item_response(response.current_task)

                    elif response.type in ("task_summary_start", "final_summary_start"):
                        yield self.create_live_update(
                            str(live_update_counter), LiveUpdateType.START, response.message or ""
                        )
                    elif response.type in ("task_completed"):
                        yield self.create_live_update(
                            str(live_update_counter), LiveUpdateType.FINISH, response.message or ""
                        )
                        if response.current_task is not None:
                            yield self.create_todo_item_response(response.current_task)
                        live_update_counter += 1

                    elif response.type in ("final_summary_end"):
                        yield self.create_live_update(
                            str(live_update_counter), LiveUpdateType.FINISH, response.message or ""
                        )
                        live_update_counter += 1
