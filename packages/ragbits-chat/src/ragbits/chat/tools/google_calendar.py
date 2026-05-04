"""Google Calendar tool for ragbits-chat."""

import json
import logging
from collections.abc import Callable
from datetime import datetime, time
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import BaseModel, Field

from ragbits.agents.tool import Tool

from ragbits.chat.interface.types import ChatContext
from ragbits.chat.tools.base import ChatTool
from ragbits.chat.tools.token_store import get_token_store

logger = logging.getLogger(__name__)

_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
_FREE_BUSY_URL = f"{_CALENDAR_API_BASE}/freeBusy"
_CALENDAR_LIST_URL = f"{_CALENDAR_API_BASE}/users/me/calendarList"

_MAX_EVENTS = 50
_MAX_ATTENDEES = 10
_DESCRIPTION_MAX = 300
_TIMEOUT = 15.0

_EVENT_TYPE_LABEL: dict[str, str] = {
    "default": "event",
    "focusTime": "focus time",
    "outOfOffice": "out of office",
    "workingLocation": "working location",
}

_RESPONSE_STATUS_LABELS: dict[str, str] = {
    "accepted": "confirmed",
    "declined": "declined",
    "tentative": "tentative",
    "needsAction": "pending",
}


# ---------------------------------------------------------------------------
# Pydantic models for Calendar API responses
# ---------------------------------------------------------------------------

class _EventTime(BaseModel):
    date_time: str | None = Field(None, alias="dateTime")
    date: str | None = None

    @property
    def value(self) -> str:
        return self.date_time or self.date or ""


class _Attendee(BaseModel):
    email: str = ""
    display_name: str | None = Field(None, alias="displayName")
    response_status: str | None = Field(None, alias="responseStatus")
    is_self: bool = Field(False, alias="self")
    is_resource: bool = Field(False, alias="resource")
    is_organizer: bool = Field(False, alias="organizer")


class _Organizer(BaseModel):
    email: str = ""
    display_name: str | None = Field(None, alias="displayName")
    is_self: bool = Field(False, alias="self")


class _ConferenceEntryPoint(BaseModel):
    entry_point_type: str = Field("", alias="entryPointType")
    uri: str = ""


class _ConferenceData(BaseModel):
    entry_points: list[_ConferenceEntryPoint] = Field(default_factory=list, alias="entryPoints")

    @property
    def video_uri(self) -> str | None:
        for ep in self.entry_points:
            if ep.entry_point_type == "video":
                return ep.uri
        return None


class _CalendarEvent(BaseModel):
    summary: str = "(No title)"
    event_type: str = Field("default", alias="eventType")
    start: _EventTime = Field(default_factory=_EventTime)
    end: _EventTime = Field(default_factory=_EventTime)
    location: str | None = None
    description: str | None = None
    organizer: _Organizer | None = None
    attendees: list[_Attendee] = Field(default_factory=list)
    conference_data: _ConferenceData | None = Field(None, alias="conferenceData")
    working_location_properties: dict | None = Field(None, alias="workingLocationProperties")

    @property
    def my_response_status(self) -> str | None:
        for a in self.attendees:
            if a.is_self:
                return a.response_status
        return None

    @property
    def people_attendees(self) -> list[_Attendee]:
        return [a for a in self.attendees if not a.is_resource]


class _EventsListResponse(BaseModel):
    items: list[_CalendarEvent] = Field(default_factory=list)
    next_page_token: str | None = Field(None, alias="nextPageToken")


class _BusyBlock(BaseModel):
    start: str = ""
    end: str = ""


class _FreeBusyCalendar(BaseModel):
    busy: list[_BusyBlock] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class _FreeBusyResponse(BaseModel):
    calendars: dict[str, _FreeBusyCalendar] = Field(default_factory=dict)


class _CalendarListEntry(BaseModel):
    id: str = ""
    summary: str = "(Unnamed)"
    primary: bool = False
    access_role: str = Field("", alias="accessRole")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_attendees(attendees: list[_Attendee]) -> str | None:
    if not attendees:
        return None
    shown = [a.display_name or a.email for a in attendees[:_MAX_ATTENDEES]]
    remaining = len(attendees) - _MAX_ATTENDEES
    result = ", ".join(shown)
    if remaining > 0:
        result += f" (+{remaining} more)"
    return result


def _format_event(event: _CalendarEvent) -> dict:
    result: dict = {
        "summary": event.summary,
        "type": _EVENT_TYPE_LABEL.get(event.event_type, event.event_type),
        "start": event.start.value,
        "end": event.end.value,
    }
    if event.organizer and not event.organizer.is_self:
        result["organizer"] = event.organizer.display_name or event.organizer.email
    my_status = event.my_response_status
    if my_status:
        result["my_status"] = _RESPONSE_STATUS_LABELS.get(my_status, my_status)
    attendees_str = _format_attendees(event.people_attendees)
    if attendees_str:
        result["attendees"] = attendees_str
    if event.location:
        result["location"] = event.location
    if event.conference_data and event.conference_data.video_uri:
        result["meet"] = event.conference_data.video_uri
    if event.description:
        truncated = event.description[:_DESCRIPTION_MAX]
        if len(event.description) > _DESCRIPTION_MAX:
            truncated += "..."
        result["description"] = truncated
    return {k: v for k, v in result.items() if v is not None}


def _format_events(events: list[_CalendarEvent]) -> str:
    if not events:
        return "No events found."
    regular = [_format_event(e) for e in events if e.event_type not in ("workingLocation",)]
    sections = []
    if regular:
        sections.append(f"Events:\n{json.dumps(regular, indent=2)}")
    return "\n\n".join(sections) if sections else "No events found."


def _ensure_rfc3339(dt_str: str, tz: ZoneInfo) -> str:
    if "T" not in dt_str:
        local_dt = datetime.combine(datetime.strptime(dt_str, "%Y-%m-%d").date(), time.min, tzinfo=tz)
        return local_dt.isoformat()
    return dt_str


# ---------------------------------------------------------------------------
# GoogleCalendarTool
# ---------------------------------------------------------------------------

class GoogleCalendarTool(ChatTool):
    """Gives the LLM access to the authenticated user's Google Calendar.

    Requires the user to grant the ``calendar`` OAuth scope via the *Connect*
    button in the Available Tools panel.

    Usage in a ``ChatInterface`` subclass::

        from ragbits.chat.tools import GoogleCalendarTool

        class MyChat(ChatInterface):
            tools = [GoogleCalendarTool()]
    """

    tool_id = "search_calendar_events"
    display_name = "📆 Calendar Events"
    category = "Utilities"
    google_scope = "calendar"

    def build(self, context: ChatContext) -> Tool:
        store = get_token_store()
        session_id = context.session_id
        user_email = context.user.email if context.user else None

        try:
            tz = ZoneInfo(context.timezone) if context.timezone else ZoneInfo("UTC")
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")

        tool_fn = self._make_search_fn(session_id=session_id, user_email=user_email, tz=tz)
        return Tool.from_callable(tool_fn)

    def _make_search_fn(
        self,
        session_id: str | None,
        user_email: str | None,
        tz: ZoneInfo,
    ) -> Callable:
        async def search_calendar_events(
            query: str = "",
            time_min: str = "",
            time_max: str = "",
            calendar_id: str = "primary",
            page_token: str = "",
        ) -> str:
            """Search Google Calendar events.

            Args:
                query: Free-text search across event titles and descriptions.
                time_min: Lower bound for event start time in RFC 3339 format
                    (e.g. '2026-04-24T00:00:00Z') or date only ('2026-04-24').
                time_max: Upper bound for event start time in RFC 3339 format or date only.
                calendar_id: Calendar to query. Use 'primary' for the user's own
                    calendar (default), or another person's email to view their calendar.
                page_token: Token from a previous response to fetch the next page of results.

            Returns:
                Formatted list of matching events with titles, times, attendees,
                locations, and meeting links.
            """
            store = get_token_store()
            token = store.get_access_token(session_id or "", "calendar") if session_id else None
            if not token:
                return "Calendar not connected. Please click the Connect button next to 'Calendar Events' in the Available Tools panel."

            url = f"{_CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='@.')}/events"
            params: dict = {
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": _MAX_EVENTS,
            }
            if query:
                params["q"] = query
            if time_min:
                params["timeMin"] = _ensure_rfc3339(time_min, tz)
            if time_max:
                params["timeMax"] = _ensure_rfc3339(time_max, tz)
            if page_token:
                params["pageToken"] = page_token

            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {token}"},
                        params=params,
                    )
                    response.raise_for_status()
                    parsed = _EventsListResponse.model_validate(response.json())
            except httpx.HTTPStatusError as e:
                logger.warning("Calendar API error %s: %s", e.response.status_code, e.response.text[:200])
                if e.response.status_code == 401:
                    return "Google Calendar access token expired. Please click Connect again in the Available Tools panel."
                if e.response.status_code == 403:
                    return "Google Calendar access denied. Please reconnect and grant calendar access in the Available Tools panel."
                return f"Calendar API error: {e.response.status_code}"
            except httpx.TimeoutException:
                return "Calendar API request timed out."

            result = _format_events(parsed.items)
            if parsed.next_page_token:
                result += f"\n\n[next_page_token: {parsed.next_page_token}]"
            return result

        return search_calendar_events
