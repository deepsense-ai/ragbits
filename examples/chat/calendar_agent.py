"""
Ragbits Chat Example: Calendar Agent with Confirmation

This example demonstrates how to use the ChatInterface with an agent that requires
user confirmation for destructive actions like deleting events or inviting people.

The confirmation is non-blocking: when a tool needs confirmation, the agent completes
its run and sends a confirmation request to the frontend. After the user confirms,
the frontend sends a new request with the confirmation, and the agent continues.

To run the script:
    ragbits api run examples.chat.calendar_agent:CalendarChat
"""

import json
import random
from collections.abc import AsyncGenerator

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import AgentRunContext
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import (
    ChatContext,
    ChatResponse,
    ChatResponseType,
    LiveUpdateType,
)
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat


# Mock database of meetings
MEETINGS_DB = {
    "meeting_001": {"title": "Team Sync", "date": "2024-11-07", "time": "14:00", "attendees": ["john@example.com"]},
    "meeting_002": {"title": "Client Call", "date": "2024-11-07", "time": "16:00", "attendees": ["jane@client.com"]},
    "meeting_003": {"title": "Sprint Planning", "date": "2024-11-08", "time": "10:00", "attendees": []},
}

# Mock employee database with OOO status
EMPLOYEES_DB = {
    "john@example.com": {"name": "John Doe", "status": "active"},
    "jane@example.com": {"name": "Jane Smith", "status": "active"},
    "bob@example.com": {"name": "Bob Wilson", "status": "ooo", "ooo_until": "2024-11-15", "auto_reply": "Out of office until Nov 15"},
    "alice@example.com": {"name": "Alice Johnson", "status": "active"},
    "charlie@example.com": {"name": "Charlie Brown", "status": "active"},
}


# Define calendar tools
def analyze_calendar() -> str:
    """Analyze the user's calendar and provide insights."""
    total_meetings = len(MEETINGS_DB)
    return f"📊 Calendar analyzed: You have {total_meetings} meetings scheduled, 2 tomorrow"


def get_meetings(date: str = "today") -> str:
    """
    Get meetings for a specific date.

    Args:
        date: Date to get meetings for (today, tomorrow, or YYYY-MM-DD)
    """
    meetings = [m for m in MEETINGS_DB.values() if date in m["date"] or date == "today"]
    if not meetings:
        return f"📅 No meetings found for {date}"

    result = f"📅 Meetings for {date}:\n"
    for meeting in meetings:
        result += f"  - {meeting['title']} at {meeting['time']}\n"
    return result


def list_meetings(date_range: str = "week") -> str:
    """
    List all meetings in a date range.

    Args:
        date_range: Range to list (today, week, month)
    """
    result = f"📋 Meetings ({date_range}):\n"
    for meeting_id, meeting in MEETINGS_DB.items():
        attendee_count = len(meeting["attendees"])
        result += f"  [{meeting_id}] {meeting['title']} - {meeting['date']} {meeting['time']} ({attendee_count} attendees)\n"
    return result


def get_availability(date: str, attendees: list[str]) -> str:
    """
    Check availability of attendees for a specific date.

    Args:
        date: Date to check (YYYY-MM-DD)
        attendees: List of email addresses to check
    """
    result = {"date": date, "available": [], "unavailable": [], "ooo": []}

    for email in attendees:
        if email in EMPLOYEES_DB:
            employee = EMPLOYEES_DB[email]
            if employee["status"] == "ooo":
                result["ooo"].append({"email": email, "name": employee["name"], "until": employee.get("ooo_until")})
            else:
                # Randomly mark some as busy for demo
                if random.random() > 0.7:
                    result["unavailable"].append({"email": email, "name": employee["name"], "reason": "Meeting conflict"})
                else:
                    result["available"].append({"email": email, "name": employee["name"]})
        else:
            result["unavailable"].append({"email": email, "name": "Unknown", "reason": "Not in directory"})

    return json.dumps(result, indent=2)


def invite_people(emails: list[str], event_id: str, message: str = "", context: AgentRunContext | None = None) -> str:
    """
    Invite multiple people to a calendar event. Requires confirmation.

    Args:
        emails: List of email addresses to invite
        event_id: ID of the event
        message: Optional message to include
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: invite_people at {timestamp}")  # noqa: T201
    print(f"   Args: emails={emails}, event_id={event_id}, message={message}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    # Simulate invitation results with some failures
    result = {
        "success": True,
        "summary": "",
        "details": {
            "event_id": event_id,
            "total_invited": 0,
            "successful": [],
            "failed": [],
            "ooo": []
        }
    }

    for email in emails:
        if email in EMPLOYEES_DB:
            employee = EMPLOYEES_DB[email]
            if employee["status"] == "ooo":
                result["details"]["ooo"].append({
                    "email": email,
                    "name": employee["name"],
                    "auto_reply": employee.get("auto_reply", "Out of office"),
                    "until": employee.get("ooo_until")
                })
            else:
                result["details"]["successful"].append({
                    "email": email,
                    "name": employee["name"],
                    "status": "invited"
                })
                result["details"]["total_invited"] += 1
        else:
            result["details"]["failed"].append({
                "email": email,
                "reason": "Email address not found in directory"
            })

    success_count = len(result["details"]["successful"])
    ooo_count = len(result["details"]["ooo"])
    fail_count = len(result["details"]["failed"])

    result["summary"] = f"✉️ Invitation results: {success_count} sent"
    if ooo_count > 0:
        result["summary"] += f", {ooo_count} out of office"
    if fail_count > 0:
        result["summary"] += f", {fail_count} failed"
        result["success"] = False

    return json.dumps(result, indent=2)


def delete_event(event_id: str, reason: str = "", context: AgentRunContext | None = None) -> str:
    """
    Delete a calendar event. Requires confirmation.

    Args:
        event_id: ID of the event to delete
        reason: Optional reason for deletion
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: delete_event at {timestamp}")  # noqa: T201
    print(f"   Args: event_id={event_id}, reason={reason}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    result = {
        "success": False,
        "summary": "",
        "details": {"event_id": event_id, "reason": reason}
    }

    if event_id in MEETINGS_DB:
        meeting = MEETINGS_DB[event_id]
        result["success"] = True
        result["summary"] = f"🗑️ Successfully deleted event '{meeting['title']}' on {meeting['date']}"
        result["details"]["deleted_meeting"] = meeting
        # Actually delete from mock DB
        del MEETINGS_DB[event_id]
    else:
        result["summary"] = f"❌ Event {event_id} not found"
        result["details"]["error"] = "Event not found in calendar"

    return json.dumps(result, indent=2)


def schedule_meeting(title: str, date: str, time: str, attendees: list[str], context: AgentRunContext | None = None) -> str:
    """
    Schedule a new meeting. Requires confirmation.

    Args:
        title: Title of the meeting
        date: Date of the meeting (YYYY-MM-DD)
        time: Time of the meeting (HH:MM)
        attendees: List of attendee email addresses
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: schedule_meeting at {timestamp}")  # noqa: T201
    print(f"   Args: title={title}, date={date}, time={time}, attendees={attendees}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    # Generate new meeting ID
    meeting_id = f"meeting_{len(MEETINGS_DB) + 1:03d}"

    # Add to mock DB
    MEETINGS_DB[meeting_id] = {
        "title": title,
        "date": date,
        "time": time,
        "attendees": attendees
    }

    result = {
        "success": True,
        "summary": f"📅 Meeting '{title}' scheduled for {date} at {time}",
        "details": {
            "meeting_id": meeting_id,
            "title": title,
            "date": date,
            "time": time,
            "attendees": attendees,
            "attendee_count": len(attendees)
        }
    }

    return json.dumps(result, indent=2)


def cancel_meeting(meeting_id: str, notify: bool = True, context: AgentRunContext | None = None) -> str:
    """
    Cancel a meeting (same as delete but with notification option). Requires confirmation.

    Args:
        meeting_id: ID of the meeting to cancel
        notify: Whether to notify attendees
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: cancel_meeting at {timestamp}")  # noqa: T201
    print(f"   Args: meeting_id={meeting_id}, notify={notify}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    result = {
        "success": False,
        "summary": "",
        "details": {"meeting_id": meeting_id, "notify": notify}
    }

    if meeting_id in MEETINGS_DB:
        meeting = MEETINGS_DB[meeting_id]
        result["success"] = True
        result["summary"] = f"❌ Canceled meeting '{meeting['title']}' on {meeting['date']}"
        if notify and meeting["attendees"]:
            result["summary"] += f" (notified {len(meeting['attendees'])} attendees)"
        result["details"]["canceled_meeting"] = meeting
        result["details"]["attendees_notified"] = meeting["attendees"] if notify else []
        # Actually delete from mock DB
        del MEETINGS_DB[meeting_id]
    else:
        result["summary"] = f"❌ Meeting {meeting_id} not found"
        result["details"]["error"] = "Meeting not found in calendar"

    return json.dumps(result, indent=2)


def reschedule_meeting(meeting_id: str, new_date: str, new_time: str, context: AgentRunContext | None = None) -> str:
    """
    Reschedule an existing meeting. Requires confirmation.

    Args:
        meeting_id: ID of the meeting to reschedule
        new_date: New date (YYYY-MM-DD)
        new_time: New time (HH:MM)
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: reschedule_meeting at {timestamp}")  # noqa: T201
    print(f"   Args: meeting_id={meeting_id}, new_date={new_date}, new_time={new_time}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    result = {
        "success": False,
        "summary": "",
        "details": {"meeting_id": meeting_id, "new_date": new_date, "new_time": new_time}
    }

    if meeting_id in MEETINGS_DB:
        meeting = MEETINGS_DB[meeting_id]
        old_date = meeting["date"]
        old_time = meeting["time"]

        # Update meeting
        MEETINGS_DB[meeting_id]["date"] = new_date
        MEETINGS_DB[meeting_id]["time"] = new_time

        result["success"] = True
        result["summary"] = f"🔄 Rescheduled '{meeting['title']}' from {old_date} {old_time} to {new_date} {new_time}"
        result["details"]["old_date"] = old_date
        result["details"]["old_time"] = old_time
        result["details"]["updated_meeting"] = MEETINGS_DB[meeting_id]
    else:
        result["summary"] = f"❌ Meeting {meeting_id} not found"
        result["details"]["error"] = "Meeting not found in calendar"

    return json.dumps(result, indent=2)


def send_reminder(meeting_id: str, attendees: list[str] | None = None, context: AgentRunContext | None = None) -> str:
    """
    Send a reminder for a meeting. Requires confirmation.

    Args:
        meeting_id: ID of the meeting
        attendees: Specific attendees to remind (None = all attendees)
        context: Agent run context (automatically injected)
    """
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    confirmed_via = "button" if (context and context.confirmed_tools) else "natural language"

    print(f"🎯 TOOL EXECUTED: send_reminder at {timestamp}")  # noqa: T201
    print(f"   Args: meeting_id={meeting_id}, attendees={attendees}")  # noqa: T201
    print(f"   Confirmed via: {confirmed_via}")  # noqa: T201

    result = {
        "success": False,
        "summary": "",
        "details": {"meeting_id": meeting_id}
    }

    if meeting_id in MEETINGS_DB:
        meeting = MEETINGS_DB[meeting_id]
        target_attendees = attendees if attendees else meeting["attendees"]

        result["success"] = True
        result["summary"] = f"🔔 Sent reminder for '{meeting['title']}' to {len(target_attendees)} attendees"
        result["details"]["meeting_title"] = meeting["title"]
        result["details"]["date"] = meeting["date"]
        result["details"]["time"] = meeting["time"]
        result["details"]["reminded"] = target_attendees
    else:
        result["summary"] = f"❌ Meeting {meeting_id} not found"
        result["details"]["error"] = "Meeting not found in calendar"

    return json.dumps(result, indent=2)


class CalendarChat(ChatInterface):
    """Calendar agent with confirmation for destructive actions."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="Calendar Assistant", subtitle="with confirmation for important actions", logo="📅"
        ),
        welcome_message=(
            "Hello! I'm your calendar assistant.\n\n"
            "I can help you manage your calendar:\n"
            "- View and analyze your schedule\n"
            "- Schedule new meetings\n"
            "- Invite people to events\n"
            "- Reschedule or cancel meetings\n"
            "- Check availability\n\n"
            "I'll ask for confirmation before making any changes."
        ),
    )

    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

        # Define tools for the agent
        self.tools = [
            # Read-only tools (no confirmation)
            analyze_calendar,
            get_meetings,
            list_meetings,
            get_availability,
            # Destructive tools (require confirmation)
            schedule_meeting,
            invite_people,
            delete_event,
            cancel_meeting,
            reschedule_meeting,
            send_reminder,
        ]

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
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
            prompt="""
            You are a helpful calendar assistant. Help users manage their calendar by:
            - Analyzing their schedule and providing insights
            - Showing meetings for specific dates or ranges
            - Checking availability of attendees before scheduling
            - Scheduling new meetings
            - Inviting people to events
            - Rescheduling or canceling meetings
            - Sending reminders

            Important guidelines:
            1. Always check availability before scheduling or inviting people
            2. When tool results contain structured data (JSON), analyze it carefully
            3. If some operations fail (e.g., OOO auto-replies), explain what happened
            4. Suggest next actions based on tool results
            5. Handle partial failures gracefully and offer solutions
            6. Parse tool results thoroughly - they contain detailed information about successes and failures

            When analyzing tool results:
            - Look for "success", "ooo", "failed" fields in the results
            - Explain any failures or issues to the user
            - Suggest remedies for failures (e.g., retry later, use different attendees)
            - If someone is out of office, tell the user when they'll be back

            Always be clear about what actions you're taking and ask for confirmation
            when needed. After executing confirmed actions, analyze the results and
            provide a helpful summary to the user.
            """,
            tools=self.tools,  # type: ignore[arg-type]
            history=history,
        )

        # Mark specific tools as requiring confirmation
        for tool in agent.tools:
            if tool.name in ["invite_people", "delete_event", "schedule_meeting",
                           "cancel_meeting", "reschedule_meeting", "send_reminder"]:
                tool.requires_confirmation = True

        # Create agent context with confirmed_tools from the request context
        agent_context: AgentRunContext = AgentRunContext()
        # Pass confirmed_tools from the chat context to the agent context
        # This allows the agent to check if any tools have been confirmed
        if context.confirmed_tools:
            agent_context.confirmed_tools = context.confirmed_tools
            print(f"✅ Set agent context with confirmed_tools: {agent_context.confirmed_tools}")  # noqa: T201

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
                    # Tool is being called
                    yield self.create_live_update(response.id, LiveUpdateType.START, f"🔧 {response.name}")

                case ConfirmationRequest():
                    # Confirmation needed - send to frontend and wait for user response
                    # The agent has already stopped execution, so this is just informing the user
                    yield ChatResponse(
                        type=ChatResponseType.CONFIRMATION_REQUEST,
                        content=response,
                    )

                case ToolCallResult():
                    # Tool execution completed (or pending confirmation)
                    result_preview = str(response.result)[:50]
                    yield self.create_live_update(
                        response.id, LiveUpdateType.FINISH, f"✅ {response.name}", result_preview
                    )

                case Usage():
                    # Usage information
                    yield self.create_usage_response(response)
