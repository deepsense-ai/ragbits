"""
Ragbits Chat Example: File Explorer Agent with Confirmation

This example demonstrates a file management agent that requires user confirmation
for all destructive operations (create, delete, move files/directories).

The agent is restricted to operating only within the temp/ directory for security.

Features:
- List files and directories
- Read file contents
- Create/delete files (with confirmation)
- Move/rename files (with confirmation)
- Create/delete directories (with confirmation)
- Search for files
- Get file information

Security:
- All paths are validated to be within temp/ directory
- Path traversal attacks are prevented
- Confirmation required for all destructive operations

To run the script:
    ragbits api run examples.chat.file_explorer_agent:FileExplorerChat
"""

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import AgentRunContext
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import requires_confirmation
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
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat

# Get the absolute path to the temp directory
TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR = TEMP_DIR.resolve()

# Ensure temp directory exists
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _validate_path(path: str) -> tuple[bool, str, Path | None]:
    """
    Validate that a path is within the temp directory.

    Args:
        path: Path to validate (relative to temp/ or absolute)

    Returns:
        Tuple of (is_valid, error_message, resolved_path)
    """
    try:
        # Handle relative paths (relative to temp/)
        full_path = TEMP_DIR / path if not os.path.isabs(path) else Path(path)

        # Resolve to absolute path and check if it's within temp/
        resolved = full_path.resolve()

        # Security check: ensure path is within TEMP_DIR
        if not str(resolved).startswith(str(TEMP_DIR)):
            return False, "Access denied: Path outside temp/ directory", None

        return True, "", resolved
    except Exception as e:
        return False, f"Invalid path: {e!s}", None


# File Explorer Tools


def list_files(directory: str = "") -> str:
    """
    List files and directories in a given path.

    Args:
        directory: Directory path (relative to temp/, empty for root)

    Returns:
        JSON string with list of files and directories
    """
    is_valid, error, dir_path = _validate_path(directory)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {
        "success": False,
        "summary": "",
        "details": {
            "directory": str(dir_path.relative_to(TEMP_DIR)) if dir_path != TEMP_DIR else ".",
            "files": [],
            "directories": [],
            "total_count": 0,
        },
    }

    try:
        if not dir_path.exists():
            result["error"] = "Directory does not exist"
            result["summary"] = f"❌ Directory '{directory}' not found"
            return json.dumps(result, indent=2)

        if not dir_path.is_dir():
            result["error"] = "Path is not a directory"
            result["summary"] = f"❌ '{directory}' is not a directory"
            return json.dumps(result, indent=2)

        for item in sorted(dir_path.iterdir()):
            item_info = {
                "name": item.name,
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime,
            }

            if item.is_file():
                result["details"]["files"].append(item_info)
            elif item.is_dir():
                result["details"]["directories"].append(item_info)

        result["success"] = True
        file_count = len(result["details"]["files"])
        dir_count = len(result["details"]["directories"])
        result["details"]["total_count"] = file_count + dir_count
        result["summary"] = f"📁 Found {file_count} files and {dir_count} directories"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error listing directory: {e!s}"

    return json.dumps(result, indent=2)


def read_file(filepath: str) -> str:
    """
    Read contents of a file.

    Args:
        filepath: Path to the file (relative to temp/)

    Returns:
        JSON string with file contents
    """
    is_valid, error, file_path = _validate_path(filepath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {
        "success": False,
        "summary": "",
        "details": {"filepath": str(file_path.relative_to(TEMP_DIR)), "content": None, "size": None},
    }

    try:
        if not file_path.exists():
            result["error"] = "File does not exist"
            result["summary"] = f"❌ File '{filepath}' not found"
            return json.dumps(result, indent=2)

        if not file_path.is_file():
            result["error"] = "Path is not a file"
            result["summary"] = f"❌ '{filepath}' is not a file"
            return json.dumps(result, indent=2)

        content = file_path.read_text()
        result["success"] = True
        result["details"]["content"] = content
        result["details"]["size"] = len(content)
        result["summary"] = f"📄 Read file '{filepath}' ({len(content)} bytes)"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error reading file: {e!s}"

    return json.dumps(result, indent=2)


def get_file_info(filepath: str) -> str:
    """
    Get detailed information about a file or directory.

    Args:
        filepath: Path to the file or directory (relative to temp/)

    Returns:
        JSON string with file information
    """
    is_valid, error, file_path = _validate_path(filepath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {"success": False, "summary": "", "details": {}}

    try:
        if not file_path.exists():
            result["error"] = "Path does not exist"
            result["summary"] = f"❌ '{filepath}' not found"
            return json.dumps(result, indent=2)

        stat_info = file_path.stat()
        result["success"] = True
        result["details"] = {
            "name": file_path.name,
            "path": str(file_path.relative_to(TEMP_DIR)),
            "type": "file" if file_path.is_file() else "directory",
            "size": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "permissions": oct(stat_info.st_mode)[-3:],
        }

        item_type = "file" if file_path.is_file() else "directory"
        result["summary"] = f"ℹ️ {item_type.capitalize()} info for '{filepath}'"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error getting info: {e!s}"

    return json.dumps(result, indent=2)


def search_files(pattern: str, directory: str = "") -> str:
    """
    Search for files matching a pattern.

    Args:
        pattern: Search pattern (glob style, e.g., "*.txt", "*report*")
        directory: Directory to search in (relative to temp/, empty for root)

    Returns:
        JSON string with search results
    """
    is_valid, error, dir_path = _validate_path(directory)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {
        "success": False,
        "summary": "",
        "details": {
            "pattern": pattern,
            "directory": str(dir_path.relative_to(TEMP_DIR)) if dir_path != TEMP_DIR else ".",
            "matches": [],
        },
    }

    try:
        if not dir_path.exists() or not dir_path.is_dir():
            result["error"] = "Directory does not exist"
            result["summary"] = f"❌ Directory '{directory}' not found"
            return json.dumps(result, indent=2)

        # Search recursively
        for match in dir_path.rglob(pattern):
            if match.is_file():
                result["details"]["matches"].append(
                    {"path": str(match.relative_to(TEMP_DIR)), "name": match.name, "size": match.stat().st_size}
                )

        result["success"] = True
        match_count = len(result["details"]["matches"])
        result["summary"] = f"🔍 Found {match_count} file(s) matching '{pattern}'"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error searching: {e!s}"

    return json.dumps(result, indent=2)


@requires_confirmation
def create_file(filepath: str, content: str, context: AgentRunContext | None = None) -> str:
    """
    Create a new file with content. Requires confirmation.

    Args:
        filepath: Path for the new file (relative to temp/)
        content: Content to write to the file
        context: Agent run context (automatically injected)

    Returns:
        JSON string with operation result
    """
    is_valid, error, file_path = _validate_path(filepath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {
        "success": False,
        "summary": "",
        "details": {"filepath": str(file_path.relative_to(TEMP_DIR)), "size": len(content)},
    }

    try:
        if file_path.exists():
            result["error"] = "File already exists"
            result["summary"] = f"❌ File '{filepath}' already exists"
            return json.dumps(result, indent=2)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content)
        result["success"] = True
        result["summary"] = f"✅ Created file '{filepath}' ({len(content)} bytes)"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error creating file: {e!s}"

    return json.dumps(result, indent=2)


@requires_confirmation
def delete_file(filepath: str, context: AgentRunContext | None = None) -> str:
    """
    Delete a file. Requires confirmation.

    Args:
        filepath: Path to the file to delete (relative to temp/)
        context: Agent run context (automatically injected)

    Returns:
        JSON string with operation result
    """
    is_valid, error, file_path = _validate_path(filepath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {"success": False, "summary": "", "details": {"filepath": str(file_path.relative_to(TEMP_DIR))}}

    try:
        if not file_path.exists():
            result["error"] = "File does not exist"
            result["summary"] = f"❌ File '{filepath}' not found"
            return json.dumps(result, indent=2)

        if not file_path.is_file():
            result["error"] = "Path is not a file (use delete_directory for directories)"
            result["summary"] = f"❌ '{filepath}' is not a file"
            return json.dumps(result, indent=2)

        size = file_path.stat().st_size
        file_path.unlink()
        result["success"] = True
        result["details"]["deleted_size"] = size
        result["summary"] = f"🗑️ Deleted file '{filepath}' ({size} bytes)"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error deleting file: {e!s}"

    return json.dumps(result, indent=2)


@requires_confirmation
def move_file(source: str, destination: str, context: AgentRunContext | None = None) -> str:
    """
    Move or rename a file. Requires confirmation.

    Args:
        source: Source file path (relative to temp/)
        destination: Destination file path (relative to temp/)
        context: Agent run context (automatically injected)

    Returns:
        JSON string with operation result
    """
    # Validate both paths
    is_valid_src, error_src, src_path = _validate_path(source)
    is_valid_dst, error_dst, dst_path = _validate_path(destination)

    if not is_valid_src:
        return json.dumps({"success": False, "error": f"Source: {error_src}"}, indent=2)
    if not is_valid_dst:
        return json.dumps({"success": False, "error": f"Destination: {error_dst}"}, indent=2)

    result = {
        "success": False,
        "summary": "",
        "details": {"source": str(src_path.relative_to(TEMP_DIR)), "destination": str(dst_path.relative_to(TEMP_DIR))},
    }

    try:
        if not src_path.exists():
            result["error"] = "Source file does not exist"
            result["summary"] = f"❌ Source file '{source}' not found"
            return json.dumps(result, indent=2)

        if not src_path.is_file():
            result["error"] = "Source is not a file"
            result["summary"] = f"❌ '{source}' is not a file"
            return json.dumps(result, indent=2)

        if dst_path.exists():
            result["error"] = "Destination already exists"
            result["summary"] = f"❌ Destination '{destination}' already exists"
            return json.dumps(result, indent=2)

        # Create destination parent directories if needed
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        src_path.rename(dst_path)
        result["success"] = True
        result["summary"] = f"🔀 Moved '{source}' to '{destination}'"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error moving file: {e!s}"

    return json.dumps(result, indent=2)


@requires_confirmation
def create_directory(dirpath: str, context: AgentRunContext | None = None) -> str:
    """
    Create a new directory. Requires confirmation.

    Args:
        dirpath: Path for the new directory (relative to temp/)
        context: Agent run context (automatically injected)

    Returns:
        JSON string with operation result
    """
    is_valid, error, dir_path = _validate_path(dirpath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {"success": False, "summary": "", "details": {"dirpath": str(dir_path.relative_to(TEMP_DIR))}}

    try:
        if dir_path.exists():
            result["error"] = "Directory already exists"
            result["summary"] = f"❌ Directory '{dirpath}' already exists"
            return json.dumps(result, indent=2)

        dir_path.mkdir(parents=True, exist_ok=False)
        result["success"] = True
        result["summary"] = f"📁 Created directory '{dirpath}'"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error creating directory: {e!s}"

    return json.dumps(result, indent=2)


@requires_confirmation
def delete_directory(dirpath: str, context: AgentRunContext | None = None) -> str:
    """
    Delete an empty directory. Requires confirmation.

    Args:
        dirpath: Path to the directory to delete (relative to temp/)
        context: Agent run context (automatically injected)

    Returns:
        JSON string with operation result
    """
    is_valid, error, dir_path = _validate_path(dirpath)
    if not is_valid:
        return json.dumps({"success": False, "error": error}, indent=2)

    result = {"success": False, "summary": "", "details": {"dirpath": str(dir_path.relative_to(TEMP_DIR))}}

    try:
        if not dir_path.exists():
            result["error"] = "Directory does not exist"
            result["summary"] = f"❌ Directory '{dirpath}' not found"
            return json.dumps(result, indent=2)

        if not dir_path.is_dir():
            result["error"] = "Path is not a directory"
            result["summary"] = f"❌ '{dirpath}' is not a directory"
            return json.dumps(result, indent=2)

        # Check if directory is empty
        if any(dir_path.iterdir()):
            result["error"] = "Directory is not empty"
            result["summary"] = f"❌ Directory '{dirpath}' is not empty. Delete contents first."
            return json.dumps(result, indent=2)

        dir_path.rmdir()
        result["success"] = True
        result["summary"] = f"🗑️ Deleted directory '{dirpath}'"

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"❌ Error deleting directory: {e!s}"

    return json.dumps(result, indent=2)


class FileExplorerChat(ChatInterface):
    """File explorer agent with confirmation for destructive actions."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="File Explorer Agent", subtitle="secure file management with confirmation", logo="📂"
        ),
        welcome_message=(
            "Hello! I'm your file explorer agent.\n\n"
            "I can help you manage files in the temp/ directory:\n"
            "- List and search files\n"
            "- Read file contents\n"
            "- Create, delete, and move files\n"
            "- Manage directories\n\n"
            "Security: All operations are restricted to the temp/ directory.\n"
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
            list_files,
            read_file,
            get_file_info,
            search_files,
            # Destructive tools (require confirmation)
            create_file,
            delete_file,
            move_file,
            create_directory,
            delete_directory,
        ]

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
            You are a file explorer agent. You have tools available.

            CRITICAL: When a user asks you to perform an action, you MUST IMMEDIATELY CALL THE APPROPRIATE TOOL.
            DO NOT ask for permission in text - the system will automatically show a confirmation dialog.
            Describe what you would do in text.

            Example:
            User: "Create folders test1 and test2"
            CORRECT: Immediately call create_directory("test1"), then create_directory("test2") return text
            "I'll create two folders for you. Please confirm action."

            Available tools: {', '.join([t.__name__ for t in self.tools])}
            Restricted to: {TEMP_DIR}
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
                    # Tool is being called
                    yield self.create_live_update(response.id, LiveUpdateType.START, f"🔧 {response.name}")

                case ConfirmationRequest():
                    # Confirmation needed - send to frontend and wait for user response
                    yield ConfirmationRequestResponse(content=ConfirmationRequestContent(confirmation_request=response))

                case ToolCallResult():
                    # Tool execution completed (or pending confirmation)
                    result_preview = str(response.result)[:50]
                    yield self.create_live_update(
                        response.id, LiveUpdateType.FINISH, f"✅ {response.name}", result_preview
                    )

                case Usage():
                    # Usage information
                    yield self.create_usage_response(response)
