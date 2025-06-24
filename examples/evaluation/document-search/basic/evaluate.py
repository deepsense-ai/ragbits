# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[chroma,hf]",
#     "ragbits-document-search[unstructured]",
#     "ragbits-evaluate[relari]",
# ]
# ///
import asyncio
import logging

from ragbits.evaluate.evaluator import Evaluator

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

config = {
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
                        "distance_method": "l2",
                        "default_options": {
                            "k": 3,
                            "score_threshold": -1.2,
                        },
                        "embedder": {
                            "type": "ragbits.core.embeddings.dense:LiteLLMEmbedder",
                            "config": {
                                "model_name": "text-embedding-3-small",
                            },
                        },
                    },
                },
                "ingest_strategy": {
                    "type": "ragbits.document_search.ingestion.strategies.batched:BatchedIngestStrategy",
                    "config": {
                        "batch_size": 10,
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
    }
}


async def evaluate() -> None:
    """
    Document search evaluation runner.
    """
    print("Starting evaluation...")

    results = await Evaluator.run_from_config(config)

    print("Computed metrics:")
    print("\n".join(f"{key}: {value}" for key, value in results.metrics.items()))

    print("Time perfs:")
    print(f"Total time: {results.time_perf.total_time_in_seconds} seconds")
    print(f"Samples per second: {results.time_perf.samples_per_second}")
    print(f"Latency: {results.time_perf.latency_in_seconds} seconds")


def main() -> None:
    """
    Runs the evaluation process.
    """
    asyncio.run(evaluate())


if __name__ == "__main__":
    main()
