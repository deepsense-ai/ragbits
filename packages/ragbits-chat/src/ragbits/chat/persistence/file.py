import json
from pathlib import Path

from ..interface.types import ChatContext, ChatResponse
from .base import HistoryPersistenceStrategy


class FileHistoryPersistence(HistoryPersistenceStrategy):
    """Strategy that saves chat history to dated files in a directory."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)

    def _get_file_path(self, conversation_id: str) -> Path:
        """Get the current conversation file path based on date and conversation ID."""
        return self.base_path / f"{conversation_id}.jsonl"

    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: list[ChatResponse],
        context: ChatContext,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction to a dated file in JSON format.

        Args:
            message: The user's input message
            response: The main response text
            extra_responses: List of additional responses (references, state updates, etc.)
            context: Optional context dictionary containing metadata
            timestamp: Unix timestamp of when the interaction occurred
        """
        # Create interaction record
        interaction = {
            "message": message,
            "context": context.model_dump(mode="json"),
            "response": response,
            "extra_responses": [r.model_dump(mode="json") for r in extra_responses],
            "timestamp": timestamp,
        }

        # Get current file path and ensure parent directory exists
        file_path = self._get_file_path(context.conversation_id or "no_conversation_id")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to file
        with open(file_path, "a") as f:
            f.write(json.dumps(interaction) + "\n")
