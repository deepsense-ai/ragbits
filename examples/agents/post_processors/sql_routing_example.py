"""
SQL Agent Routing Example

This example demonstrates how to use RoutePostProcessor and RerunPostProcessor to create
a multi-agent system that routes natural language queries to a SQL agent and retries
on failures - equivalent to Pydantic AI's ModelRetry pattern.

The pipeline shows:
- Router agent that routes queries to specialized agents
- SQL agent with retry logic for unsupported queries
- Conditional routing based on query type

To run the script, execute:
    ```bash
    uv run examples/agents/post_processors/sql_routing_example.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents",
# ]
# ///

import asyncio
import re

from pydantic import BaseModel

from ragbits.agents import Agent, AgentResult
from ragbits.agents.post_processors import RerunPostProcessor, RoutePostProcessor
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class Row(BaseModel):
    """Represents a row in the database."""

    name: str
    country: str


class SQLFailure(BaseModel):
    """An unrecoverable failure. Only use this when you can't change the query to make it work."""

    explanation: str


tables = {
    "capital_cities": [
        Row(name="Amsterdam", country="Netherlands"),
        Row(name="Mexico City", country="Mexico"),
    ]
}


class SQLAgentInput(BaseModel):
    """Input format for the SQL agent."""

    query: str


class SQLAgentPrompt(Prompt[SQLAgentInput, str]):
    """Prompt for the SQL agent."""

    system_prompt = (
        "You are a SQL agent that can run SQL queries on a database. Specifically SELECT * FROM capital_cities"
    )
    user_prompt = "{{ query }}"


class RouterAgentInput(BaseModel):
    """Input format for the router agent."""

    query: str


class RouterAgentOutput(BaseModel):
    """Output format for the router agent."""

    should_route: bool
    original_query: str


class RouterAgentPrompt(Prompt[RouterAgentInput, RouterAgentOutput]):
    """Prompt for the router agent."""

    system_prompt = "You are a router to other agents. Never try to solve a problem yourself, just pass it on."
    user_prompt = "{{ query }}"


def run_sql_query(result: AgentResult) -> list[Row] | SQLFailure:
    """
    Run a SQL query on the database.
    Returns query results or SQLFailure with feedback for retry.
    """
    query = str(result.content)
    select_table = re.match(r"SELECT (.+) FROM (\w+)", query, re.IGNORECASE)
    if not select_table:
        return SQLFailure(explanation=f"Unsupported query: '{query}'.")

    column_names = select_table.group(1).strip()
    if column_names != "*":
        return SQLFailure(explanation="Only 'SELECT *' is supported, you'll have to do column filtering manually.")

    table_name = select_table.group(2)
    if table_name not in tables:
        available = ", ".join(tables.keys())
        return SQLFailure(
            explanation=f"Unknown table '{table_name}' in query '{query}'. Available tables: {available}."
        )

    return tables[table_name]


def generate_rerun_input(failure: SQLFailure, attempt: int) -> SQLAgentInput:
    """Generate rerun input from failure, including context from the original attempt."""
    return SQLAgentInput(
        query=f"Your previous SQL query had an error. Please fix it and try again.\n\nError: {failure.explanation}"
    )


def should_route_to_sql(result: AgentResult[RouterAgentOutput]) -> bool:
    """Determine if router should hand off to SQL agent."""
    return result.content.should_route


def router_input_for_sql(result: AgentResult[RouterAgentOutput]) -> SQLAgentInput:
    """Extract the actual query from router's decision."""
    return SQLAgentInput(query=result.content.original_query)


async def main() -> None:
    """Run the SQL routing example."""
    llm = LiteLLM("gpt-5", use_structured_output=True)

    # SQL Agent with RerunPostProcessor (handles retries like ModelRetry)
    sql_agent = Agent(
        name="sql_agent",
        llm=llm,
        prompt=SQLAgentPrompt,
        post_processors=[
            RerunPostProcessor(
                process_fn=run_sql_query,  # Validates and executes SQL query
                failure_type=SQLFailure,  # Check if output is SQLFailure
                rerun_input_fn=generate_rerun_input,  # Generate feedback from failure
                max_retries=2,
            )
        ],
    )

    # Router Agent with RoutePostProcessor (hands off to specialized agents)
    router_agent = Agent(
        name="router_agent",
        llm=llm,
        prompt=RouterAgentPrompt,
        post_processors=[
            RoutePostProcessor(
                target_agent=sql_agent,
                should_route=should_route_to_sql,
                input_fn=router_input_for_sql,
                combine_results=True,
            )
        ],
    )

    # Run a single test query
    query = "Select the names and countries of all capitals"
    result = await router_agent.run(RouterAgentInput(query=query))
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
