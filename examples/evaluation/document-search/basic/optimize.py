# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[chroma]",
#     "ragbits-document-search[huggingface]",
#     "ragbits-evaluate[relari]",
# ]
# ///
import logging
from pathlib import Path

from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.utils import log_optimization_to_file

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

config = {
    "optimizer": {
        "direction": "maximize",
        "n_trials": 5,
    },
    "experiment": {
        "dataloader": {
            "type": "ragbits.evaluate.loaders.hf:HFDataLoader",
            "config": {
                "path": "micpst/hf-docs-retrieval",
                "split": "train",
            },
        },
        "pipeline": {
            "type": "ragbits.evaluate.pipelines.document_search:DocumentSearch",
            "config": {
                "embedder": {
                    "type": "ragbits.core.embeddings.litellm:LiteLLMEmbeddings",
                    "config": {
                        "model": "text-embedding-3-small",
                        "default_options": {
                            "dimensions": {
                                "optimize": True,
                                "range": [32, 512],
                            },
                        },
                    },
                },
                "providers": {
                    "txt": {
                        "type": "ragbits.document_search.ingestion.providers.unstructured:UnstructuredDefaultProvider",
                    },
                },
                "source": {
                    "type": "ragbits.document_search.documents.sources:HuggingFaceSource",
                    "config": {
                        "path": "micpst/hf-docs",
                        "split": "train[:5]",
                    },
                },
            },
        },
        "metrics": {
            "precision_recall_f1": {
                "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                "config": {
                    "matching_strategy": {
                        "type": "RougeChunkMatch",
                        "config": {
                            "threshold": 0.5,
                        },
                    },
                },
            },
        },
    },
}


def main() -> None:
    """
    Runs the optimization process.
    """
    print("Starting optimization...")

    configs_with_scores = Optimizer.run_from_config(config)

    output_dir = log_optimization_to_file(configs_with_scores, Path("optimization"))
    print(f"Optimization results saved under directory: {output_dir}")


if __name__ == "__main__":
    main()
