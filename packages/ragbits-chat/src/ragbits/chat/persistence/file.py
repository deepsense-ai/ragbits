import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from ..interface.types import ChatContext, ChatResponse
from .base import HistoryPersistenceStrategy


class FileHistoryPersistence(HistoryPersistenceStrategy):
    """Strategy that saves chat history to dated files in a directory."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)

    def _get_file_path(self, conversation_id: str) -> Path:
        """Get the current conversation file path based on date and conversation ID."""
        return self.base_path / f"{conversation_id}.jsonl"

    def _get_all_conversation_files(self) -> list[Path]:
        """Get all conversation files in the base directory."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        return list(self.base_path.glob("*.jsonl"))

    @staticmethod
    def _load_interactions_from_file(file_path: Path) -> list[dict[str, Any]]:
        """Load all interactions from a conversation file."""
        interactions = []
        if file_path.exists():
            with open(file_path) as f:
                for raw_line in f:
                    stripped_line = raw_line.strip()
                    if stripped_line:
                        interactions.append(json.loads(stripped_line))
        return interactions

    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: Sequence[ChatResponse],
        context: ChatContext,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction to a dated file in JSON format.

        Args:
            message: The user's input message.
            response: The main response text.
            extra_responses: List of additional responses (references, state updates, etc.).
            context: Context dictionary containing metadata.
            timestamp: Unix timestamp of when the interaction occurred.
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

    async def get_conversation_interactions(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all interactions for a given conversation.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of interaction dictionaries with deserialized data.
        """
        file_path = self._get_file_path(conversation_id)
        interactions = self._load_interactions_from_file(file_path)

        return [
            {
                "id": idx,
                "conversation_id": conversation_id,
                "message_id": interaction.get("context", {}).get("message_id"),
                "message": interaction["message"],
                "response": interaction["response"],
                "extra_responses": interaction.get("extra_responses", []),
                "context": interaction.get("context", {}),
                "timestamp": interaction["timestamp"],
                "created_at": datetime.fromtimestamp(interaction["timestamp"]),
            }
            for idx, interaction in enumerate(interactions)
        ]

    async def get_conversation_count(self) -> int:
        """
        Get the total number of conversations.

        Returns:
            The total count of conversations.
        """
        return len(self._get_all_conversation_files())

    async def get_total_interactions_count(self) -> int:
        """
        Get the total number of chat interactions across all conversations.

        Returns:
            The total count of interactions.
        """
        total = 0
        for file_path in self._get_all_conversation_files():
            interactions = self._load_interactions_from_file(file_path)
            total += len(interactions)
        return total

    async def get_recent_conversations(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent conversations.

        Args:
            limit: Maximum number of conversations to retrieve.

        Returns:
            List of conversation dictionaries with metadata including id, created_at,
            and interaction_count.
        """
        conversation_files = self._get_all_conversation_files()

        # Get metadata for each conversation
        conversations = []
        for file_path in conversation_files:
            interactions = self._load_interactions_from_file(file_path)
            if interactions:
                # Get the earliest timestamp as created_at
                timestamps = [i["timestamp"] for i in interactions]
                created_at = datetime.fromtimestamp(min(timestamps))
                last_activity = max(timestamps)

                conversations.append(
                    {
                        "id": file_path.stem,
                        "created_at": created_at,
                        "interaction_count": len(interactions),
                        "_last_activity": last_activity,
                    }
                )

        # Sort by last activity (most recent first) and limit
        conversations.sort(key=lambda x: x["_last_activity"], reverse=True)
        return [
            {"id": c["id"], "created_at": c["created_at"], "interaction_count": c["interaction_count"]}
            for c in conversations[:limit]
        ]

    async def search_interactions(
        self,
        query: str,
        search_in_messages: bool = True,
        search_in_responses: bool = True,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for interactions containing specific text.

        Args:
            query: Text to search for.
            search_in_messages: Whether to search in user messages.
            search_in_responses: Whether to search in assistant responses.
            limit: Maximum number of results.

        Returns:
            List of matching interactions with id, conversation_id, message_id,
            message, response, and timestamp.
        """
        results = []
        query_lower = query.lower()

        for file_path in self._get_all_conversation_files():
            conversation_id = file_path.stem
            interactions = self._load_interactions_from_file(file_path)

            for idx, interaction in enumerate(interactions):
                message_match = search_in_messages and query_lower in interaction["message"].lower()
                response_match = search_in_responses and query_lower in interaction["response"].lower()

                if message_match or response_match:
                    results.append(
                        {
                            "id": idx,
                            "conversation_id": conversation_id,
                            "message_id": interaction.get("context", {}).get("message_id"),
                            "message": interaction["message"],
                            "response": interaction["response"],
                            "timestamp": interaction["timestamp"],
                        }
                    )

                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]

    async def get_interactions_by_date_range(
        self,
        start_timestamp: float,
        end_timestamp: float,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get interactions within a specific time range.

        Args:
            start_timestamp: Start of the time range (Unix timestamp).
            end_timestamp: End of the time range (Unix timestamp).
            conversation_id: Optional conversation ID to filter by.

        Returns:
            List of interactions in the time range.
        """
        results = []

        files = [self._get_file_path(conversation_id)] if conversation_id else self._get_all_conversation_files()

        for file_path in files:
            if not file_path.exists():
                continue

            conv_id = file_path.stem
            interactions = self._load_interactions_from_file(file_path)

            for idx, interaction in enumerate(interactions):
                ts = interaction["timestamp"]
                if start_timestamp <= ts <= end_timestamp:
                    results.append(
                        {
                            "id": idx,
                            "conversation_id": conv_id,
                            "message_id": interaction.get("context", {}).get("message_id"),
                            "message": interaction["message"],
                            "response": interaction["response"],
                            "timestamp": ts,
                            "created_at": datetime.fromtimestamp(ts),
                        }
                    )

        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"])
        return results

    async def export_conversation(
        self,
        conversation_id: str,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """
        Export a complete conversation with all metadata.

        Args:
            conversation_id: The conversation to export.
            include_metadata: Whether to include extra metadata in interactions.

        Returns:
            Dictionary containing conversation_id, export_timestamp, interaction_count,
            and interactions list.
        """
        interactions = await self.get_conversation_interactions(conversation_id)

        export_data: dict[str, Any] = {
            "conversation_id": conversation_id,
            "export_timestamp": datetime.now().isoformat(),
            "interaction_count": len(interactions),
            "interactions": interactions
            if include_metadata
            else [
                {
                    "message": i["message"],
                    "response": i["response"],
                    "timestamp": i["timestamp"],
                }
                for i in interactions
            ],
        }

        return export_data

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its interactions.

        Args:
            conversation_id: The conversation to delete.

        Returns:
            True if the conversation was deleted, False if it didn't exist.
        """
        file_path = self._get_file_path(conversation_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def get_conversation_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics about stored conversations.

        Returns:
            Dictionary containing total_conversations, total_interactions,
            avg_interactions_per_conversation, first_interaction, last_interaction,
            avg_message_length, and avg_response_length.
        """
        conversation_count = await self.get_conversation_count()
        total_interactions = 0
        all_timestamps: list[float] = []
        total_message_length = 0
        total_response_length = 0

        for file_path in self._get_all_conversation_files():
            interactions = self._load_interactions_from_file(file_path)
            total_interactions += len(interactions)

            for interaction in interactions:
                all_timestamps.append(interaction["timestamp"])
                total_message_length += len(interaction["message"])
                total_response_length += len(interaction["response"])

        avg_interactions = total_interactions / conversation_count if conversation_count > 0 else 0
        avg_message_length = total_message_length / total_interactions if total_interactions > 0 else 0
        avg_response_length = total_response_length / total_interactions if total_interactions > 0 else 0

        return {
            "total_conversations": conversation_count,
            "total_interactions": total_interactions,
            "avg_interactions_per_conversation": round(avg_interactions, 2),
            "first_interaction": datetime.fromtimestamp(min(all_timestamps)).isoformat() if all_timestamps else None,
            "last_interaction": datetime.fromtimestamp(max(all_timestamps)).isoformat() if all_timestamps else None,
            "avg_message_length": round(avg_message_length, 2),
            "avg_response_length": round(avg_response_length, 2),
        }
