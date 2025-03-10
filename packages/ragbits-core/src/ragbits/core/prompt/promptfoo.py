import os
from pathlib import Path

try:
    import yaml

    HAS_PYYAML = True
except ImportError:
    HAS_PYYAML = False

from rich.console import Console

from ragbits.core.config import core_config
from ragbits.core.prompt.discovery import PromptDiscovery


def generate_configs(
    file_pattern: str = core_config.prompt_path_pattern,
    root_path: Path | None = None,
    target_path: Path = Path("promptfooconfigs"),
) -> None:
    """
    Generates promptfoo configuration files for all discovered prompts.

    Args:
        file_pattern: The file pattern to search for Prompt objects. Defaults to "**/prompt_*.py"
        root_path: The root path to search for Prompt objects. Defaults to the directory where the script is run.
        target_path: The path to save the promptfoo configuration files. Defaults to "promptfooconfigs".
    """
    root_path = root_path or Path.cwd()

    if not HAS_PYYAML:
        Console(stderr=True).print(
            "To generate configs for promptfoo, you need the PyYAML library. Please install it using the following"
            " command:\n[b]pip install ragbits-core\\[promptfoo][/b]"
        )
        return

    prompts = PromptDiscovery(file_pattern=file_pattern, root_path=root_path).discover()
    Console().print(
        f"Discovered {len(prompts)} prompts."
        f" Saving promptfoo configuration files to [bold green]{target_path}[/] folder ..."
    )

    if not target_path.exists():
        target_path.mkdir()
    for prompt in prompts:
        with open(target_path / f"{prompt.__qualname__}.yaml", "w", encoding="utf-8") as f:
            prompt_path = f"file://{prompt.__module__.replace('.', os.sep)}.py:{prompt.__qualname__}.to_promptfoo"
            yaml.dump({"prompts": [prompt_path]}, f)
