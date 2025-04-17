from functools import cached_property
from pathlib import Path

from pydantic import BaseModel

from ragbits.core.llms.base import LLMType
from ragbits.core.utils._pyproject import get_config_from_yaml, get_config_instance
from ragbits.core.utils.config_handling import import_by_path


class CoreConfig(BaseModel):
    """
    Configuration for the ragbits-core package, loaded from downstream projects' pyproject.toml files.
    """

    # Path to the base directory of the project, defaults to the directory of the pyproject.toml file
    project_base_path: Path | None = None

    # Pattern used to search for prompt files
    prompt_path_pattern: str = "**/prompt_*.py"

    # Path to a functions that returns LLM objects, e.g. "my_project.llms.get_llm"
    llm_preference_factories: dict[LLMType, str] = {
        LLMType.TEXT: "ragbits.core.llms.factory:simple_litellm_factory",
        LLMType.VISION: "ragbits.core.llms.factory:simple_litellm_vision_factory",
        LLMType.STRUCTURED_OUTPUT: "ragbits.core.llms.factory:simple_litellm_structured_output_factory",
    }

    # Path to functions that returns instances of diffrent types of Ragbits objects
    component_preference_factories: dict[str, str] = {}

    # Path to a YAML file with preferred configuration of varius Ragbits objects
    component_preference_config_path: Path | None = None

    modules_to_import: dict[str, list[str]] = {}

    @cached_property
    def preferred_instances_config(self) -> dict:
        """
        Get the configuration from the file specified in component_preference_config_path.

        Returns:
            dict: The configuration from the file.
        """
        if self.component_preference_config_path is None or not self.project_base_path:
            return {}

        return get_config_from_yaml(self.project_base_path / self.component_preference_config_path)


core_config = get_config_instance(CoreConfig, subproject="core")


def import_modules_from_config(config_key: str, config: CoreConfig = core_config) -> None:
    """
    A function that imports all modules specified in config instance for given key
    Args:
        config_key: str configuration key
        config: CoreConfig instance of configuration
    """
    paths_to_import = config.modules_to_import.get(config_key)
    if paths_to_import:
        for path in paths_to_import:
            import_by_path(path)
