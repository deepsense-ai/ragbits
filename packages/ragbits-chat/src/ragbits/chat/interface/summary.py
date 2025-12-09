import asyncio
import logging
from abc import ABC, abstractmethod

from ragbits.chat.interface.types import ChatContext
from ragbits.core.llms.base import LLM
from ragbits.core.prompt.base import ChatFormat

logger = logging.getLogger(__name__)


class SummaryGenerator(ABC):
    """Base class for summary generators."""

    @abstractmethod
    async def generate(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Generate a concise conversation title."""
        ...


class HeuristicSummaryGenerator(SummaryGenerator):
    """Simple title generator using heuristics (no LLM)."""

    SIMPLE_MESSAGE_LENGTH = 2

    def __init__(self, max_words: int = 6, fallback_title: str = "New chat"):
        self.max_words = max_words
        self.fallback_title = fallback_title

    async def generate(self, message: str, _history: ChatFormat, _context: ChatContext) -> str:
        """Generate a concise conversation title using heuristic approach."""
        t = (message or "").strip()
        if not t or len(t.split()) <= self.SIMPLE_MESSAGE_LENGTH:
            return self.fallback_title
        return " ".join(t.split()[: self.max_words])


class LLMSummaryGenerator(SummaryGenerator):
    """Generates a short conversation title using an LLM."""

    DEFAULT_PROMPT = (
        "You are a concise title generator for conversation threads. "
        "Given the user's first message, return a single short title (3–8 words) summarizing the topic. "
        "If the message is just a greeting or otherwise generic, respond exactly with: New chat\n\n"
        "User message:\n{message}\n\nTitle:"
    )
    DEFAULT_TIMEOUT = 5

    def __init__(self, llm: LLM, timeout: int = DEFAULT_TIMEOUT, prompt_template: str | None = None):
        self.llm = llm
        self.timeout = timeout
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT

    async def generate(self, message: str, _history: ChatFormat, _context: ChatContext) -> str:
        """Generate a concise conversation title using LLM."""
        prompt = self.prompt_template.format(message=message)
        try:
            raw = await asyncio.wait_for(self.llm.generate(prompt), self.timeout)
            title = str(raw).strip().splitlines()[0]
            return title or "New chat"
        except asyncio.TimeoutError:
            logger.warning("LLM title generation timed out — using fallback.")
            return "New chat"
        except Exception:
            logger.exception("Error generating title with LLM — using fallback.")
            return "New chat"


class HybridSummaryGenerator(SummaryGenerator):
    """Generates a short conversation title using an LLM with heuristic approach as a fallback."""

    def __init__(self, llm: LLM):
        self.llm_gen = LLMSummaryGenerator(llm)
        self.heuristic = HeuristicSummaryGenerator()

    async def generate(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Generate summary using either LLM with heuristic approach as a fallback."""
        try:
            title = await self.llm_gen.generate(message, history, context)
            return title or await self.heuristic.generate(message, history, context)
        except Exception:
            return await self.heuristic.generate(message, history, context)
