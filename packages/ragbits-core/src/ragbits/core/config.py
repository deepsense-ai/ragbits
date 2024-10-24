from pydantic import BaseModel

from ragbits.core.utils._pyproject import get_config_instance


class CoreConfig(BaseModel):
    """
    Configuration for the ragbits-core package, loaded from downstream projects' pyproject.toml files.
    """

    # Pattern used to search for prompt files
    prompt_path_pattern: str = "**/prompt_*.py"

    # Path to a function that returns an LLM object, e.g. "my_project.llms.get_llm"
    default_llm_factory: str | None = None


core_config = get_config_instance(CoreConfig, subproject="core")
