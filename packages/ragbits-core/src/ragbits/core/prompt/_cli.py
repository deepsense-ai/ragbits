import asyncio
import inspect
import json
from importlib import import_module
from pathlib import Path

import typer
from pydantic import BaseModel

from ragbits.cli import print_output
from ragbits.core.config import core_config
from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.prompt.discovery import PromptDiscovery
from ragbits.core.prompt.prompt import ChatFormat, Prompt

prompts_app = typer.Typer(no_args_is_help=True)


class LLMResponseCliOutput(BaseModel):
    """An output model for llm responses in CLI"""

    question: ChatFormat
    answer: str | BaseModel | None = None


class PromptInfo(BaseModel):
    """Information about a Prompt class for CLI display"""

    name: str
    import_path: str
    description: str
    input_type: str
    output_type: str


def _render(prompt_path: str, payload: str | None) -> Prompt:
    module_stringified, object_stringified = prompt_path.split(":")
    prompt_cls = getattr(import_module(module_stringified), object_stringified)

    if payload is not None:
        payload = json.loads(payload)
        inputs = prompt_cls.input_type(**payload)
        return prompt_cls(inputs)

    return prompt_cls()


@prompts_app.command()
def promptfoo(
    file_pattern: str = core_config.prompt_path_pattern,
    root_path: Path = Path.cwd(),  # noqa: B008
    target_path: Path = Path("promptfooconfigs"),
) -> None:
    """
    Generates the configuration files for the PromptFoo prompts.

    For more information, see the [Promptfoo integration documentation](../how-to/prompts/promptfoo.md).
    """
    from ragbits.core.prompt.promptfoo import generate_configs

    generate_configs(file_pattern=file_pattern, root_path=root_path, target_path=target_path)


@prompts_app.command()
def search(file_pattern: str = core_config.prompt_path_pattern, root_path: Path = Path.cwd()) -> None:  # noqa: B008
    """
    Lists all available prompts that can be used with the 'render' and 'exec' commands.
    """
    prompt_classes = PromptDiscovery(file_pattern=file_pattern, root_path=root_path).discover()
    prompt_infos = [
        PromptInfo(
            name=prompt_cls.__name__,
            import_path=f"{prompt_cls.__module__}:{prompt_cls.__name__}",
            description=inspect.getdoc(prompt_cls) or "",
            input_type=getattr(prompt_cls.input_type, "__name__", str(prompt_cls.input_type)),
            output_type=getattr(prompt_cls.output_type, "__name__", str(prompt_cls.output_type)),
        )
        for prompt_cls in prompt_classes
    ]
    print_output(prompt_infos)


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
    llm_factory: str = core_config.llm_preference_factories[LLMType.TEXT],
) -> None:
    """
    Executes a prompt using the specified prompt class and LLM factory.
    """
    prompt = _render(prompt_path=prompt_path, payload=payload)

    if llm_factory is None:
        raise ValueError("`llm_factory` must be provided")
    llm: LLM = LLM.subclass_from_factory(llm_factory)

    llm_output = asyncio.run(llm.generate(prompt))
    response = LLMResponseCliOutput(question=prompt.chat, answer=llm_output)
    print_output(response)
