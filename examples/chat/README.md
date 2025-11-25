# Chat Examples

This directory contains examples demonstrating the Ragbits Chat Interface with various configurations and features.

## Examples Overview

### Basic Chat Examples

- **[chat.py](chat.py)** - Simple chat application
- **[offline_chat.py](offline_chat.py)** - Chat application that works offline
- **[recontextualize_message.py](recontextualize_message.py)** - Message compression and recontextualization
- **[tutorial.py](tutorial.py)** - Tutorial example for getting started
- **[themed_chat.py](themed_chat.py)** - Chat with custom theming (uses custom-theme.json)
- **[authenticated_chat.py](authenticated_chat.py)** - Chat with authentication (see [README_authenticated.md](README_authenticated.md))
- **[hiking_agent.py](hiking_agent.py)** - Hiking trip planning agent

### Agent Examples with Confirmation

These examples demonstrate agents that require user confirmation for destructive or important actions. The confirmation system is **stateless** - all state is managed in the frontend (IndexedDB/Zustand), allowing the agents to scale horizontally without server-side session management.

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
   - Uses pattern matching to find \*.md files

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
       if tool.name in ["delete_file", "create_file", "delete_directory"]:
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
User: "Create files test1.txt and test2.txt"
Agent: [Shows confirmation for file creation]
User: "Actually, only create test1.txt"
Agent: [Creates NEW confirmation with updated parameters]
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
# Run file explorer agent with confirmation
ragbits api run examples.chat.file_explorer_agent:FileExplorerChat

# Run basic chat
ragbits api run examples.chat.chat:chat

# Run themed chat
ragbits api run examples.chat.themed_chat:themed_chat

# Run hiking agent
ragbits api run examples.chat.hiking_agent:hiking_agent

# Run authenticated chat (see README_authenticated.md for setup)
ragbits api run examples.chat.authenticated_chat:authenticated_chat
```

All examples will start a web server with the Ragbits UI where you can interact with the agents.

## Testing

The `temp/` directory contains sample files for testing the file explorer agent:

- `temp/README.txt` - Overview file
- `temp/documents/report.txt` - Sample document
- `temp/documents/notes.md` - Sample markdown file
- `temp/images/photo1.jpg` - Placeholder image file

Feel free to create, modify, and delete files through the agent!
