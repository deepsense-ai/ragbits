# pylint: disable=import-outside-toplevel
# pylint: disable=missing-param-doc
import asyncio
import json
from importlib import import_module
from pathlib import Path

import typer
from rich import print as pprint

from ragbits.core.config import core_config
from ragbits.core.llms.base import LLMType
from ragbits.core.prompt.prompt import Prompt


def _render(prompt_path: str, payload: str | None) -> Prompt:
    module_stringified, object_stringified = prompt_path.split(":")
    prompt_cls = getattr(import_module(module_stringified), object_stringified)

    if payload is not None:
        payload = json.loads(payload)
        inputs = prompt_cls.input_type(**payload)
        return prompt_cls(inputs)

    return prompt_cls()


prompts_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """

    @prompts_app.command()
    def lab(
        file_pattern: str = core_config.prompt_path_pattern,
        llm_factory: str | None = core_config.default_llm_factories[LLMType.TEXT],
    ) -> None:
        """
        Launches the interactive application for listing, rendering, and testing prompts
        defined within the current project.
        """
        from ragbits.core.prompt.lab.app import lab_app

        lab_app(file_pattern=file_pattern, llm_factory=llm_factory)

    @prompts_app.command()
    def generate_promptfoo_configs(
        file_pattern: str = core_config.prompt_path_pattern,
        root_path: Path = Path.cwd(),  # noqa: B008
        target_path: Path = Path("promptfooconfigs"),
    ) -> None:
        """
        Generates the configuration files for the PromptFoo prompts.
        """
        from ragbits.core.prompt.promptfoo import generate_configs

        generate_configs(file_pattern=file_pattern, root_path=root_path, target_path=target_path)

    @prompts_app.command()
    def render(prompt_path: str, payload: str | None = None) -> None:
        """
        Renders a prompt by loading a class from a module and initializing it with a given payload.
        """
        prompt = _render(prompt_path=prompt_path, payload=payload)

        pprint("[orange3]RENDERED PROMPT:")
        pprint(prompt.chat)

    @prompts_app.command(name="exec")
    def execute(
        prompt_path: str,
        payload: str | None = None,
        llm_factory: str | None = core_config.default_llm_factories[LLMType.TEXT],
    ) -> None:
        """
        Executes a prompt using the specified prompt class and LLM factory.

        Raises:
            ValueError: If `llm_factory` is not provided.
        """
        from ragbits.core.llms.factory import get_llm_from_factory

        prompt = _render(prompt_path=prompt_path, payload=payload)

        if llm_factory is None:
            raise ValueError("`llm_factory` must be provided")
        llm = get_llm_from_factory(llm_factory)

        response = asyncio.run(llm.generate(prompt))

        pprint("[orange3]QUESTION:")
        pprint(prompt.chat)
        pprint("[orange3]ANSWER:")
        pprint(response)

    app.add_typer(prompts_app, name="prompts", help="Commands for managing prompts")
