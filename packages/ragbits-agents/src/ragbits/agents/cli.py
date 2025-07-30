import asyncio
import json

import typer

from ragbits.agents import Agent
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT

agents_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(agents_app, name="agents", help="Commands for managing agents")


def _create_prompt_input(
    prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | Prompt[PromptInputT, PromptOutputT] | None,
    payload: str | None,
) -> str | PromptInputT | None:
    if prompt is None or isinstance(prompt, str):
        return payload
    elif (
        payload
        and (isinstance(prompt, type) and issubclass(prompt, Prompt) or isinstance(prompt, Prompt))
        and prompt.input_type is not None
    ):
        loaded_payload = json.loads(payload) if payload else {}
        return prompt.input_type(**loaded_payload)
    raise ValueError("Invalid combination of prompt and payload")


@agents_app.command(name="exec")
def execute(agent_factory: str, payload: str | None = None) -> None:
    """
    Executes an agent using the specified prompt class and LLM factory.
    """
    if agent_factory is None:
        raise ValueError("`agent_factory` must be provided")
    agent: Agent = Agent.subclass_from_factory(agent_factory)

    agent_output = asyncio.run(agent.run(_create_prompt_input(agent.prompt, payload)))
    print(agent_output)


@agents_app.command()
def run(agent_factory: str, payload: str | None = None) -> None:
    """
    Executes an agent using the specified prompt class and LLM factory and enters interactive mode.
    """
    if agent_factory is None:
        raise ValueError("`agent_factory` must be provided")
    agent: Agent = Agent.subclass_from_factory(agent_factory)
    agent.keep_history = True

    agent_output = asyncio.run(agent.run(_create_prompt_input(agent.prompt, payload)))
    typer.echo(agent_output)
    typer.echo("Entering interactive mode. Type exit to finish chat.")

    interactive_agent: Agent = Agent(
        agent.llm,
        prompt="You are a helpful assistant.",
        history=agent.history,
        keep_history=agent.keep_history,
        mcp_servers=agent.mcp_servers,
        default_options=agent.default_options,
    )
    interactive_agent.tools = agent.tools
    while True:
        try:
            user_input = typer.prompt(">>>")
            if user_input.lower() == "exit":
                break

            result = asyncio.run(interactive_agent.run(user_input))
            typer.echo(result)
        except (KeyboardInterrupt, EOFError):
            break
    typer.echo("Goodbye!")
