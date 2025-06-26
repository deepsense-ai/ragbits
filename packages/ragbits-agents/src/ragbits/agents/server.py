from urllib.parse import urlparse

import uvicorn
from a2a.types import AgentCard
from fastapi import FastAPI
from pydantic import BaseModel

from ragbits.agents import Agent, AgentResult


class Request(BaseModel):
    """
    Represents a request to the agent server.
    """

    method: str
    params: dict


class Response(BaseModel):
    """
    Represents a response from the agent server.
    """

    result: dict | None = None
    error: str | None = None


def _format_response(result: AgentResult) -> dict:
    return {
        "content": result.content,
        "metadata": result.metadata,
        "tool_calls": [t.__dict__ for t in result.tool_calls or []],
    }


def create_agent_server(agent: Agent, agent_card: AgentCard, input_model: BaseModel) -> FastAPI:
    """
    Create a FastAPI server for the given agent and input schema.
    The server exposes:
        - GET /.well-known/agent.json: Returns the agent's metadata.
        - POST /: Accepts structured input and returns the agent's output.

    Args:
        agent: An instance of the ragbits Agent to expose.
        agent_card: Metadata describing the agent.
        input_model: A Pydantic model describing the input format.

    Returns:
        FastAPI: The configured FastAPI app.
    """
    app = FastAPI(title=agent_card.name, description=agent_card.description)

    @app.get("/.well-known/agent.json", response_model=AgentCard)
    async def get_card() -> AgentCard:
        return agent_card

    @app.post("/", response_model=Response)
    async def handle(request: Request) -> Response:
        try:
            input = input_model(**request.params)
            result = await agent.run(input)

            return Response(result=_format_response(result))

        except Exception as e:
            return Response(error=str(e))

    return app


def run_agent_server(agent: Agent, agent_card: AgentCard, input_model: BaseModel) -> None:
    """
    Run a Uvicorn server that serves the given agent over HTTP.
    Uses the host and port specified in the agent_card URL.

    Args:
        agent: The ragbits Agent instance to serve.
        agent_card: The agent's metadata including name, description, and URL.
        input_model: A Pydantic model for validating input parameters.
    """
    app = create_agent_server(agent=agent, agent_card=agent_card, input_model=input_model)
    url = urlparse(agent_card.url)

    uvicorn.run(app, host=url.hostname, port=url.port)
