from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from ragbits.core.prompt.base import ChatFormat


class ConversationPipelineState(BaseModel):
    """
    Dataclass that represents the state of the conversation pipeline.
    """

    user_question: str
    session_id: str | None = None
    client_metada: dict[str, Any] = {}
    history: ChatFormat = []
    rag_context: list[str] = []

    # Additional metadata from plugins that will be returned to the client.
    plugin_metadata: dict[str, Any] = {}


@dataclass
class ConversationPipelineResult:
    """
    Dataclass that represents the result of the conversation pipeline.
    """

    plugin_metadata: dict[str, Any]
    output_stream: AsyncGenerator[str, None]
