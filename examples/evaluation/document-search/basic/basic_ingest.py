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

from omegaconf import OmegaConf

from ragbits.evaluate.pipelines import pipeline_factory

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


async def ingest() -> None:
    """
    Ingest documents into the document search system.

    Args:
        config: Hydra configuration.
    """
    log.info("Ingesting documents...")

    config = OmegaConf.create(
        {
            "type": "ragbits.evaluate.pipelines.document_search:DocumentSearchWithIngestionPipeline",
            "ingest": True,
            "search": False,
            "answer_data_source": {"name": "hf-docs", "path": "micpst/hf-docs", "split": "train", "num_docs": 5},
            "providers": {
                "txt": {"type": "ragbits.document_search.ingestion.providers.unstructured:UnstructuredDefaultProvider"}
            },
        }
    )

    ingestor = pipeline_factory(config)  # type: ignore

    await ingestor()

    log.info("Ingestion finished.")


def main() -> None:
    """
    Run the ingestion process.

    Args:
        config: Hydra configuration.
    """
    asyncio.run(ingest())


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
