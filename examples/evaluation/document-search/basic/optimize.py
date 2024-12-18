import sys

from omegaconf import OmegaConf

from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.utils import log_optimization_to_file

module = sys.modules[__name__]


def main() -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in config.
    """
    config = OmegaConf.create(
        {
            "pipeline": {
                "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchWithIngestionPipeline",
                "ingest": True,
                "search": True,
                "answer_data_source": {
                    "name": "hf-docs",
                    "path": "micpst/hf-docs",
                    "split": "train",
                    "num_docs": 5,
                },
                "providers": {
                    "txt": {
                        "type": "ragbits.document_search.ingestion.providers.unstructured:UnstructuredDefaultProvider"
                    }
                },
                "embedder": {
                    "type": "ragbits.core.embeddings.litellm:LiteLLMEmbeddings",
                    "config": {
                        "model": "text-embedding-3-small",
                        "options": {
                            "dimensions": {"optimize": True, "range": [32, 512]},
                        },
                    },
                },
            },
            "data": {
                "type": "ragbits.evaluate.loaders.hf:HFDataLoader",
                "options": {"name": "hf-docs-retrieval", "path": "micpst/hf-docs-retrieval", "split": "train"},
            },
            "metrics": [
                {
                    "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                    "matching_strategy": "RougeChunkMatch",
                    "options": {"threshold": 0.5},
                }
            ],
        }
    )
    config = {"optimizer": OmegaConf.create({"direction": "maximize", "n_trials": 10}), "experiment_config": config}
    configs_with_scores = Optimizer.run_experiment_from_config(config=config)
    log_optimization_to_file(configs_with_scores)


if __name__ == "__main__":
    main()
