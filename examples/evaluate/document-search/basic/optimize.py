"""
Ragbits Evaluate Example: Basic Document Search Optimization

This example demonstrates how to optimize a basic document search pipeline using the `Optimizer` class.
It configures a simple pipeline with ChromaDB as the vector store, LiteLLMEmbedder for embeddings, and HuggingFaceSource for data.

To run the script, execute the following command:

    ```bash
    uv run examples/evaluate/document-search/basic/optimize.py
    ```
"""  # noqa: E501

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[chroma,hf]",
#     "ragbits-document-search",
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
        "max_retries_for_trial": 1,
    },
    "evaluator": {
        "evaluation": {
            "dataloader": {
                "type": "ragbits.evaluate.dataloaders.document_search:DocumentSearchDataLoader",
                "config": {
                    "source": {
                        "type": "ragbits.core.sources:HuggingFaceSource",
                        "config": {
                            "path": "deepsense-ai/synthetic-rag-dataset_v1.0",
                            "split": "train",
                        },
                    },
                },
            },
            "pipeline": {
                "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchPipeline",
                "config": {
                    "vector_store": {
                        "type": "ragbits.core.vector_stores.chroma:ChromaVectorStore",
                        "config": {
                            "client": {
                                "type": "EphemeralClient",
                            },
                            "index_name": "baseline",
                            "embedder": {
                                "type": "ragbits.core.embeddings.dense:LiteLLMEmbedder",
                                "config": {
                                    "model_name": "text-embedding-3-small",
                                    "default_options": {
                                        "dimensions": {
                                            "optimize": True,
                                            "range": [32, 512],
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "parser_router": {
                        "txt": {
                            "type": "ragbits.document_search.ingestion.parsers.unstructured:UnstructuredDocumentParser",
                        },
                    },
                    "source": {
                        "type": "ragbits.core.sources:HuggingFaceSource",
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
