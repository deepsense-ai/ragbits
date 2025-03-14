from ragbits.core.config import CoreConfig
from ragbits.core.utils._pyproject import get_config_instance


class EvaluateConfig(CoreConfig):
    """Configuration of ragbits evaluate module"""

    component_preference_factories: dict[str, str] = {"metrics": "ragbits.evaluate.factories:precision_recall_f1"}

    dataloader_default_class: str = "ragbits.evaluate.dataloaders.hf:HFDataLoader"

    default_input_schemas_for_pipelines: dict[str, dict] = {
        "document_search_evaluation": {
            "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchDatapointSchema",
            "config": {"question_col": "question", "reference_passage_col": "passage"},
        }
    }


eval_config = get_config_instance(EvaluateConfig, subproject="evaluate")
