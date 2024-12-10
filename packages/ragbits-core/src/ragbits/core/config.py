from functools import cached_property
from pathlib import Path

from pydantic import BaseModel

from ragbits.core.llms.base import LLMType
from ragbits.core.utils._pyproject import get_config_from_yaml, get_config_instance


class CoreConfig(BaseModel):
    """
    Configuration for the ragbits-core package, loaded from downstream projects' pyproject.toml files.
    """

    # Path to the base directory of the project, defaults to the directory of the pyproject.toml file
    project_base_path: Path | None = None

    # Pattern used to search for prompt files
    prompt_path_pattern: str = "**/prompt_*.py"

    # Path to a functions that returns LLM objects, e.g. "my_project.llms.get_llm"
    default_llm_factories: dict[LLMType, str] = {
        LLMType.TEXT: "ragbits.core.llms.factory:simple_litellm_factory",
        LLMType.VISION: "ragbits.core.llms.factory:simple_litellm_vision_factory",
        LLMType.STRUCTURED_OUTPUT: "ragbits.core.llms.factory:simple_litellm_structured_output_factory",
    }

    # Path to functions that returns instances of diffrent types of Ragbits objects
    default_factories: dict[str, str] = {}

    # Path to a YAML file with default configuration of varius Ragbits objects
    default_instaces_config_path: Path | None = None

    @cached_property
    def default_instances_config(self) -> dict:
        """
        Get the configuration from the file specified in default_instaces_config_path.

        Returns:
            dict: The configuration from the file.
        """
        if self.default_instaces_config_path is None or not self.project_base_path:
            return {}

        return get_config_from_yaml(self.project_base_path / self.default_instaces_config_path)


core_config = get_config_instance(CoreConfig, subproject="core")
