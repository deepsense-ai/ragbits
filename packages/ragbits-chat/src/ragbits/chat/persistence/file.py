import json
from pathlib import Path

from ..interface.types import ChatResponse
from .base import HistoryPersistenceStrategy


class FileHistoryPersistence(HistoryPersistenceStrategy):
    """Strategy that saves chat history to a file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: list[ChatResponse],
        context: dict | None,
        timestamp: float,
    ) -> None:
        # Create interaction record
        interaction = {
            "message": message,
            "context": context,
            "response": response,
            "extra_responses": [r.model_dump() for r in extra_responses],
            "timestamp": timestamp,
        }

        # Append to file
        with open(self.file_path, "a") as f:
            f.write(json.dumps(interaction) + "\n")
