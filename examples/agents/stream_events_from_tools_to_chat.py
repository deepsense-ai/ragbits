"""
Ragbits Agents Example: Streaming custom events from tools

This example demonstrates how to define a tool that emits custom ChatResponse
events (e.g. a chart to be rendered by the UI) while streaming, and how to
consume those events inside a ChatInterface served via RagbitsAPI.

To run the API, use the following command:

    ```bash
    uvicorn examples.agents.stream_events_from_tools_to_chat:app
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents",
#     "ragbits-chat",
# ]
# ///

from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass

from ragbits.agents import Agent
from ragbits.agents.tool import ToolReturn
from ragbits.chat.api import RagbitsAPI
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, TextContent, TextResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt.base import ChatFormat

# ---------------------------------------------------------------------------
# Mock data source
# ---------------------------------------------------------------------------


@dataclass
class RevenueData:
    """Represent revenue data from each quarter."""

    quarters: list[str]
    revenue: list[float]


def fetch_revenue_data(year: int) -> RevenueData | None:
    """Return dummy quarterly revenue data for a given year."""
    catalog = {
        2023: RevenueData(quarters=["Q1", "Q2", "Q3", "Q4"], revenue=[100.0, 150.0, 120.0, 180.0]),
        2024: RevenueData(quarters=["Q1", "Q2", "Q3", "Q4"], revenue=[200.0, 250.0, 220.0, 300.0]),
    }
    return catalog.get(year)


# ---------------------------------------------------------------------------
# Streaming tool
# ---------------------------------------------------------------------------


def display_revenue_table(year: int) -> Generator[TextResponse | ToolReturn]:
    """Fetches revenue data (in thousands of dollars) for the given year and displays it as a Markdown table.

    Args:
        year: The year to fetch revenue data for.
    """
    data = fetch_revenue_data(year)
    if data is None:
        yield ToolReturn(value=f"No data for year {year}")
    else:
        rows = "\n".join(f"| {q} | {v} |" for q, v in zip(data.quarters, data.revenue, strict=False))
        table = f"\n\n| Quarter | Value |\n|---------|-------|\n{rows}\n\n"
        yield TextResponse(content=TextContent(text=table))
        yield ToolReturn(value={"year": year, "total": sum(data.revenue)})


# ---------------------------------------------------------------------------
# Chat interface
# ---------------------------------------------------------------------------


class RevenueChatInterface(ChatInterface):
    """Chat interface with a tool that streams revenue tables."""

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o")
        self.agent = Agent(
            llm=self.llm,
            prompt="""
            You are a helpful revenue analytics assistant. Use `display_revenue_table` to show revenue data to the user.
            Invoking that tool means that the user sees the table in the web interface. When invoking that tool,
            do not write the data yourself.

            You have access to data from 2023 and 2024.""",
            tools=[display_revenue_table],
        )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handles interaction with the user."""
        async for chunk in self.agent.run_streaming(message):
            if isinstance(chunk, str):
                yield self.create_text_response(chunk)
            elif isinstance(chunk, TextResponse):
                yield chunk


app = RagbitsAPI(RevenueChatInterface).app
