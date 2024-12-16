import asyncio
import json
from importlib import import_module
from pathlib import Path

import typer
from pydantic import BaseModel

from ragbits.cli import print_output
from ragbits.core.config import core_config
from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.prompt.prompt import ChatFormat, Prompt

prompts_app = typer.Typer(no_args_is_help=True)


class LLMResponseCliOutput(BaseModel):
    """An output model for llm responses in CLI"""

    question: ChatFormat
    answer: str | BaseModel | None = None


def _render(prompt_path: str, payload: str | None) -> Prompt:
    module_stringified, object_stringified = prompt_path.split(":")
    prompt_cls = getattr(import_module(module_stringified), object_stringified)

    if payload is not None:
        payload = json.loads(payload)
        inputs = prompt_cls.input_type(**payload)
        return prompt_cls(inputs)

    return prompt_cls()


@prompts_app.command()
def lab(
    file_pattern: str = core_config.prompt_path_pattern,
    llm_factory: str = core_config.default_llm_factories[LLMType.TEXT],
) -> None:
    """
    Launches the interactive application for listing, rendering, and testing prompts
    defined within the current project.

    For more information, see the [Prompts Lab documentation](../how-to/prompts_lab.md).
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

    For more information, see the [Promptfoo integration documentation](../how-to/integrations/promptfoo.md).
    """
    from ragbits.core.prompt.promptfoo import generate_configs

    generate_configs(file_pattern=file_pattern, root_path=root_path, target_path=target_path)


@prompts_app.command()
def render(prompt_path: str, payload: str | None = None) -> None:
    """
    Renders a prompt by loading a class from a module and initializing it with a given payload.
    """
    prompt = _render(prompt_path=prompt_path, payload=payload)
    response = LLMResponseCliOutput(question=prompt.chat)
    print_output(response)


@prompts_app.command(name="exec")
def execute(
    prompt_path: str,
    payload: str | None = None,
    llm_factory: str = core_config.default_llm_factories[LLMType.TEXT],
) -> None:
    """
    Executes a prompt using the specified prompt class and LLM factory.

    For an example of how to use this command, see the [Quickstart guide](../quickstart/quickstart1_prompts.md).
    """
    prompt = _render(prompt_path=prompt_path, payload=payload)

    if llm_factory is None:
        raise ValueError("`llm_factory` must be provided")
    llm: LLM = LLM.subclass_from_factory(llm_factory)

    llm_output = asyncio.run(llm.generate(prompt))
    response = LLMResponseCliOutput(question=prompt.chat, answer=llm_output)
    print_output(response)
