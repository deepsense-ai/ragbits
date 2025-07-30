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

    prompt_input = _create_prompt_input(agent.prompt, payload)
    print(prompt_input)
    agent_output = asyncio.run(agent.run(prompt_input))
    print(agent_output)
