# pylint: disable=import-outside-toplevel
# pylint: disable=missing-param-doc
from pathlib import Path

import typer

from ragbits.core.config import core_config

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
        llm_factory: str | None = core_config.default_llm_factory,
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

    app.add_typer(prompts_app, name="prompts", help="Commands for managing prompts")
