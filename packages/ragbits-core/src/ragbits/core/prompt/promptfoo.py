import os
from pathlib import Path

import yaml
from rich.console import Console

from ragbits.core.prompt.discovery import PromptDiscovery
from ragbits.core.prompt.discovery.prompt_discovery import DEFAULT_FILE_PATTERN


def generate_configs(
    file_pattern: str = DEFAULT_FILE_PATTERN,
    root_path: Path = Path.cwd(),
    target_path: Path = Path("promptfooconfigs"),
) -> None:
    """
    Generates promptfoo configuration files for all discovered prompts.

    Args:
        file_pattern: The file pattern to search for Prompt objects. Defaults to "**/prompt_*.py"
        root_path: The root path to search for Prompt objects. Defaults to the directory where the script is run.
        target_path: The path to save the promptfoo configuration files. Defaults to "promptfooconfigs".
    """
    prompts = PromptDiscovery(file_pattern=file_pattern, root_path=root_path).discover()
    Console().print(
        f"Discovered {len(prompts)} prompts."
        f" Saving promptfoo configuration files to [bold green]{target_path}[/] folder ..."
    )

    if not target_path.exists():
        target_path.mkdir()
    for prompt in prompts:
        with open(target_path / f"{prompt.__qualname__}.yaml", "w", encoding="utf-8") as f:
            prompt_path = f'file://{prompt.__module__.replace(".", os.sep)}.py:{prompt.__qualname__}.to_promptfoo'
            yaml.dump({"prompts": [prompt_path]}, f)
