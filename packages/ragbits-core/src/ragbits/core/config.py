from pydantic import BaseModel

from ragbits.core.llms.base import LLMType
from ragbits.core.utils._pyproject import get_config_instance


class CoreConfig(BaseModel):
    """
    Configuration for the ragbits-core package, loaded from downstream projects' pyproject.toml files.
    """

    # Pattern used to search for prompt files
    prompt_path_pattern: str = "**/prompt_*.py"

    # Path to a functions that returns LLM objects, e.g. "my_project.llms.get_llm"
    default_llm_factories: dict[LLMType, str | None] = {
        LLMType.TEXT: None,
        LLMType.VISION: None,
        LLMType.STRUCTURED_OUTPUT: None,
    }


core_config = get_config_instance(CoreConfig, subproject="core")
