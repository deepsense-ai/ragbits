from ragbits.core.config import CoreConfig
from ragbits.core.utils._pyproject import get_config_instance


class EvaluateConfig(CoreConfig):
    """
    Configuration for the ragbits-evaluate package, loaded from downstream projects' pyproject.toml files.
    """

    default_input_schemas_for_pipelines: dict[str, dict] = {
        "document_search_evaluation": {
            "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchDatapointSchema",
            "config": {"question_col": "question", "reference_passage_col": "passage"},
        }
    }


eval_config = get_config_instance(EvaluateConfig, subproject="evaluate")
