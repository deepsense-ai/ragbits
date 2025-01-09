# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search[huggingface]",
#     "ragbits-core[chroma]",
#     "hydra-core~=1.3.2",
#     "unstructured[md]>=0.15.13",
# ]
# ///
import asyncio
import logging
import uuid
from pathlib import Path

from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.utils import log_to_file

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


async def evaluate() -> dict:
    """
    Basic example of document search evaluation.

    """
    log.info("Ingesting documents...")

    config = {
        "pipeline": {
            "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchWithIngestionPipeline",
            "ingest": False,
            "search": True,
            "vector_store": {
                "type": "ragbits.core.vector_stores.chroma:ChromaVectorStore",
                "config": {
                    "client": {"type": "PersistentClient", "config": {"path": "chroma"}},
                    "index_name": "default",
                    "distance_method": "l2",
                    "default_options": {"k": 3, "max_distance": 1.2},
                },
            },
            "providers": {
                "txt": {"type": "ragbits.document_search.ingestion.providers.unstructured:UnstructuredDefaultProvider"}
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
        "neptune": {"project": "ragbits", "run": False},
        "task": {"name": "default", "type": "document-search"},
    }

    results = await Evaluator.run_experiment_from_config(config=config)

    log.info("Evaluation finished.")

    return results


def main() -> None:
    """
    Run the evaluation process.

    """
    results = asyncio.run(evaluate())
    out_dir = Path(str(uuid.uuid4()))
    out_dir.mkdir()
    log_to_file(results, output_dir=out_dir)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
