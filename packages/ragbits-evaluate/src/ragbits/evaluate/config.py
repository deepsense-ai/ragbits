from ragbits.core.config import CoreConfig
from ragbits.core.utils._pyproject import get_config_instance


class EvaluateConfig(CoreConfig):
    """Configuration of ragbits evaluate module"""
    default_factories: dict[str, str] = {
        "evaluation_target": "ragbits.evaluate.factories.target:default_evaluation_target"
    }


eval_config = get_config_instance(EvaluateConfig, subproject="evaluate")
