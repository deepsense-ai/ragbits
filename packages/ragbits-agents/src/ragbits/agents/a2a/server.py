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
        "history": result.history,
        "tool_calls": [t.__dict__ for t in result.tool_calls or []],
    }


def create_agent_app(agent: Agent, agent_card: "AgentCard", input_model: type[BaseModel]) -> "FastAPI":
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


def create_agent_server(
    agent: Agent,
    agent_card: "AgentCard",
    input_model: type[BaseModel],
) -> "uvicorn.Server":
    """
    Create a Uvicorn server instance that serves the specified agent over HTTP.

    The server's host and port are extracted from the URL in the given agent_card.

    Args:
        agent: The Ragbits Agent instance to serve.
        agent_card: Metadata for the agent, including its URL.
        input_model: A Pydantic model class used to validate incoming request data.

    Returns:
        A configured uvicorn.Server instance ready to be started.

    Raises:
        ValueError: If the URL in agent_card does not contain a valid hostname or port.
    """
    app = create_agent_app(agent=agent, agent_card=agent_card, input_model=input_model)
    url = urlparse(agent_card.url)

    if not url.hostname:
        raise ValueError(f"Could not parse hostname from URL: {agent_card.url}")
    if not url.port:
        raise ValueError(f"Could not parse port from URL: {agent_card.url}")

    config = uvicorn.Config(app=app, host=url.hostname, port=url.port)
    server = uvicorn.Server(config=config)

    return server
