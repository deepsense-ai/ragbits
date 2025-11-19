# Chat Examples

This directory contains examples demonstrating the Ragbits Chat Interface with various agent configurations.

## Examples Overview

### Basic Chat Examples

- **[chat.py](chat.py)** - Simple chat application
- **[offline_chat.py](offline_chat.py)** - Chat application that works offline
- **[recontextualize_message.py](recontextualize_message.py)** - Message compression and recontextualization

### Agent Examples with Confirmation

These examples demonstrate agents that require user confirmation for destructive or important actions. The confirmation system is **stateless** - all state is managed in the frontend (IndexedDB/Zustand), allowing the agents to scale horizontally without server-side session management.

#### Calendar Agent ([calendar_agent.py](calendar_agent.py))

A calendar management agent with the following features:

**Tools:**
- `analyze_calendar()` - Analyze schedule and provide insights
- `get_meetings(date)` - Get meetings for a specific date
- `list_meetings(date_range)` - List all meetings in a range
- `get_availability(date, attendees)` - Check attendee availability
- `schedule_meeting(title, date, time, attendees)` - **Requires confirmation**
- `invite_people(emails, event_id, message)` - **Requires confirmation**
- `delete_event(event_id, reason)` - **Requires confirmation**
- `cancel_meeting(meeting_id, notify)` - **Requires confirmation**
- `reschedule_meeting(meeting_id, new_date, new_time)` - **Requires confirmation**
- `send_reminder(meeting_id, attendees)` - **Requires confirmation**

**Key Features:**
- **Rich Tool Results**: Tools return structured JSON with detailed success/failure information
- **Partial Failure Handling**: When inviting multiple people, some may succeed while others fail (e.g., out of office)
- **Intelligent Analysis**: Agent analyzes tool results and provides helpful summaries
- **State Management**: Uses mock database (MEETINGS_DB, EMPLOYEES_DB) that persists across tool calls

**Example Scenarios:**
```bash
# Run the agent
ragbits api run examples.chat.calendar_agent:CalendarChat
```

Try these interactions:
1. "Invite john@example.com, bob@example.com, and alice@example.com to meeting_001"
   - Result: Bob will have OOO auto-reply, others invited successfully
   - Agent explains the partial failure and suggests next steps

2. "Schedule a meeting for tomorrow at 3pm with the team"
   - Agent asks for confirmation
   - Creates meeting and returns meeting ID

3. "Check availability for john@example.com and bob@example.com on 2024-11-10"
   - Shows who's available vs. out of office
   - No confirmation needed (read-only)

#### File Explorer Agent ([file_explorer_agent.py](file_explorer_agent.py))

A secure file management agent restricted to the `temp/` directory:

**Tools:**
- `list_files(directory)` - List files and directories
- `read_file(filepath)` - Read file contents
- `get_file_info(filepath)` - Get detailed file information
- `search_files(pattern, directory)` - Search for files by pattern
- `create_file(filepath, content)` - **Requires confirmation**
- `delete_file(filepath)` - **Requires confirmation**
- `move_file(source, destination)` - **Requires confirmation**
- `create_directory(dirpath)` - **Requires confirmation**
- `delete_directory(dirpath)` - **Requires confirmation**

**Security Features:**
- **Path Validation**: All paths are validated to be within `temp/` directory
- **Path Traversal Prevention**: `../` and absolute paths outside temp/ are blocked
- **Automatic Path Resolution**: Paths are automatically resolved and checked
- **Confirmation Required**: All file modifications require user confirmation

**Key Features:**
- **Detailed Results**: Every operation returns structured JSON with success/failure info
- **Error Handling**: Clear error messages for common issues (file not found, already exists, etc.)
- **Directory Restrictions**: Cannot delete non-empty directories
- **Rich File Info**: File size, permissions, modification times

**Example Scenarios:**
```bash
# Run the agent
ragbits api run examples.chat.file_explorer_agent:FileExplorerChat
```

Try these interactions:
1. "List all files in the documents folder"
   - Shows files with sizes and counts

2. "Read the report.txt file"
   - Displays file contents

3. "Create a new file called 'todo.txt' with my task list"
   - Agent asks for confirmation
   - Creates file with specified content

4. "Search for all markdown files"
   - Uses pattern matching to find *.md files

5. "Try to access /etc/passwd" (security test)
   - Agent will reject: "Access denied: Path outside temp/ directory"

6. "Delete documents/report.txt"
   - Agent asks for confirmation
   - Deletes file and reports size

## Confirmation System Architecture

### How It Works

1. **Agent marks tools with confirmation:**
   ```python
   for tool in agent.tools:
       if tool.name in ["delete_file", "invite_people", ...]:
           tool.requires_confirmation = True
   ```

2. **When confirmation needed:**
   - Agent yields `ConfirmationRequest` with tool details
   - Frontend displays confirmation dialog
   - Agent stops execution (stateless)

3. **User confirms:**
   - Frontend sends new message with `confirmed_tools` in context
   - Agent re-runs, finds matching confirmation_id, executes tool
   - Agent analyzes results and responds

4. **State Management:**
   - All confirmation state stored in frontend (IndexedDB)
   - No server-side sessions required
   - Agents are completely stateless
   - History contains full context

### Modifying Confirmations

Users can modify tool parameters before confirming:

```
User: "Invite john@ex.com, bob@ex.com, alice@ex.com to meeting_001"
Agent: [Shows confirmation with 3 people]
User: "Actually, don't invite Bob"
Agent: [Creates NEW confirmation with 2 people, marks old one superseded]
User: [Confirms]
Agent: Executes with modified parameters
```

### Rich Tool Results

Tools return structured JSON for intelligent agent analysis:

```json
{
  "success": true/false,
  "summary": "Human-readable summary",
  "details": {
    "successful": [...],
    "failed": [...],
    "ooo": [...]
  }
}
```

This allows the agent to:
- Explain what succeeded and what failed
- Suggest remedies for failures
- Provide contextual information
- Offer next steps

## Running the Examples

```bash
# Run calendar agent
ragbits api run examples.chat.calendar_agent:CalendarChat

# Run file explorer agent
ragbits api run examples.chat.file_explorer_agent:FileExplorerChat
```

Both examples will start a web server with the Ragbits UI where you can interact with the agents.

## Testing

The `temp/` directory contains sample files for testing the file explorer agent:
- `temp/README.txt` - Overview file
- `temp/documents/report.txt` - Sample document
- `temp/documents/notes.md` - Sample markdown file
- `temp/images/photo1.jpg` - Placeholder image file

Feel free to create, modify, and delete files through the agent!





