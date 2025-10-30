"""
Ragbits Chat Example: Calendar Agent with Confirmation

This example demonstrates how to use the ChatInterface with an agent that requires
user confirmation for destructive actions like deleting events or inviting people.

To run the script:
    ragbits api run examples.chat.calendar_agent:CalendarChat
"""

from collections.abc import AsyncGenerator
from types import SimpleNamespace

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import AgentDependencies, AgentRunContext, DownstreamAgentResult
from ragbits.agents.confirmation import ConfirmationManager, ConfirmationRequest
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat
from ragbits.core.prompt.base import BasePrompt


# Define calendar tools
def analyze_calendar() -> str:
    """Analyze the user's calendar and provide insights."""
    return "📊 Calendar analyzed: You have 5 meetings this week, 2 tomorrow"


def get_meetings(date: str = "today") -> str:
    """
    Get meetings for a specific date.

    Args:
        date: Date to get meetings for (today, tomorrow, or YYYY-MM-DD)
    """
    return f"📅 Meetings for {date}: Team sync (2pm), Client call (4pm)"


def invite_people(email: str, event_id: str, message: str = "") -> str:
    """
    Invite people to a calendar event.

    Args:
        email: Email address of the person to invite
        event_id: ID of the event
        message: Optional message to include
    """
    return f"✉️ Successfully invited {email} to event {event_id}"


def delete_event(event_id: str, reason: str = "") -> str:
    """
    Delete a calendar event.

    Args:
        event_id: ID of the event to delete
        reason: Optional reason for deletion
    """
    return f"🗑️ Successfully deleted event {event_id}"


# Type alias for response types
ResponseType = (
    str | ToolCall | ToolCallResult | ConfirmationRequest | BasePrompt | Usage | SimpleNamespace | DownstreamAgentResult
)


class CalendarChat(ChatInterface):
    """Calendar agent with confirmation for destructive actions."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="Calendar Assistant", subtitle="with confirmation for important actions", logo="📅"
        ),
        welcome_message=(
            "Hello! I'm your calendar assistant.\n\n"
            "I can help you manage your calendar, but I'll ask for confirmation "
            "before deleting events or inviting people."
        ),
    )

    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

        # Create agent with tools marked for confirmation
        self.agent: Agent = Agent(
            llm=self.llm,
            prompt="""
            You are a helpful calendar assistant. Help users manage their calendar by:
            - Analyzing their schedule
            - Showing meetings
            - Inviting people to events
            - Deleting events when requested

            Always be clear about what actions you're taking.
            """,
            tools=[
                analyze_calendar,
                get_meetings,
                invite_people,
                delete_event,
            ],
            keep_history=True,
        )
        # Mark specific tools as requiring confirmation
        for tool in self.agent.tools:
            if tool.name in ["invite_people", "delete_event"]:
                tool.requires_confirmation = True

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Chat implementation with confirmation support."""
        # Get the confirmation manager from context (provided by RagbitsAPI)
        confirmation_manager: ConfirmationManager = context.confirmation_manager  # type: ignore[attr-defined]

        # Create a simple namespace to hold our dependencies
        deps_value = SimpleNamespace(confirmation_manager=confirmation_manager)
        agent_context: AgentRunContext = AgentRunContext(deps=AgentDependencies(value=deps_value))

        # Run agent in streaming mode with just the message (agent handles history internally)
        async for response in self.agent.run_streaming(
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
                    # Tool is being called
                    yield self.create_live_update(response.id, LiveUpdateType.START, f"🔧 {response.name}")

                case ConfirmationRequest():
                    # Confirmation needed - send to frontend
                    yield ChatResponse(
                        type=ChatResponseType.CONFIRMATION_REQUEST,
                        content=response,
                    )

                case ToolCallResult():
                    # Tool execution completed
                    result_preview = str(response.result)[:50]
                    yield self.create_live_update(
                        response.id, LiveUpdateType.FINISH, f"✅ {response.name}", result_preview
                    )

                case Usage():
                    # Usage information
                    yield self.create_usage_response(response)
