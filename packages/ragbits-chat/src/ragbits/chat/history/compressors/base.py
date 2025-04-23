from abc import ABC, abstractmethod
from typing import ClassVar

from ragbits.chat.history import compressors
from ragbits.core.prompt.base import ChatFormat
from ragbits.core.utils.config_handling import WithConstructionConfig


class ConversationHistoryCompressor(WithConstructionConfig, ABC):
    """
    An abstract class for conversation history compressors,
    i.e. class that takes the entire conversation history
    and returns a single string representation of it.

    The exact logic of what the string should include and represent
    depends on the specific implementation.

    Usually used to provide LLM additional context from the conversation history.
    """

    default_module: ClassVar = compressors
    configuration_key: ClassVar = "history_compressor"

    @abstractmethod
    async def compress(self, conversation: ChatFormat) -> str:
        """
        Compresses the conversation history to a single string.

        Args:
            conversation:  List of dicts with "role" and "content" keys, representing the chat history so far.
        """
