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

import hydra
from omegaconf import DictConfig
from tqdm.asyncio import tqdm

from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.sources import HuggingFaceSource

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


async def ingest(config: DictConfig) -> None:
    """
    Ingest documents into the document search system.

    Args:
        config: Hydra configuration.
    """
    log.info("Ingesting documents...")

    document_search = DocumentSearch.from_config(config.pipeline)  # type: ignore

    documents = await tqdm.gather(
        *[
            DocumentMeta.from_source(
                HuggingFaceSource(
                    path=config.data.path,
                    split=config.data.split,
                    row=i,
                )
            )
            for i in range(config.data.num_docs)
        ],
        desc="Download",
    )

    await document_search.ingest(documents)

    log.info("Ingestion finished.")


@hydra.main(config_path="config", config_name="ingestion", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Run the ingestion process.

    Args:
        config: Hydra configuration.
    """
    asyncio.run(ingest(config))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
