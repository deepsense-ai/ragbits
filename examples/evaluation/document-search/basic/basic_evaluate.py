# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search[huggingface]",
#     "ragbits-core[chroma]",
#     "ragbits-evaluate[relari]",
#     "hydra-core~=1.3.2",
#     "unstructured[md]>=0.15.13",
# ]
# ///
import asyncio
import logging

from ragbits.evaluate.evaluator import Evaluator

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

config = {
    "dataloader": {
        "type": "ragbits.evaluate.loaders.hf:HFDataLoader",
        "config": {
            "path": "micpst/hf-docs-retrieval",
            "split": "train",
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
                    "distance_method": "l2",
                    "default_options": {
                        "k": 3,
                        "max_distance": 1.2,
                    },
                },
            },
            "providers": {
                "txt": {
                    "type": "ragbits.document_search.ingestion.providers.unstructured:UnstructuredDefaultProvider",
                },
            },
            "processing_strategy": {
                "type": "ragbits.document_search.ingestion.processor_strategies.batched:BatchedAsyncProcessing",
                "config": {
                    "batch_size": 10,
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
        "concurrency": 10,
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
    "loggers": {
        "local": True,
        "neptune": False,
    },
}


async def evaluate() -> None:
    """
    Document search evaluation runner.
    """
    print("Starting evaluation...")
    results = await Evaluator.run_from_config(config)
    print("Computed metrics:\n{}".format("\n".join(f"{key}: {value}" for key, value in results["metrics"].items())))


def main() -> None:
    """
    Run the evaluation process.
    """
    asyncio.run(evaluate())


if __name__ == "__main__":
    main()
