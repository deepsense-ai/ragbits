# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-evaluate[relari]",
#     "ragbits-core[chroma]",
# ]
# ///
import asyncio
import logging

import hydra
from omegaconf import DictConfig

from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.loaders import dataloader_factory
from ragbits.evaluate.metrics import metric_set_factory
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline
from ragbits.evaluate.utils import log_to_file, log_to_neptune, setup_neptune

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


async def bench(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    run = setup_neptune(config)
    log.info("Starting the experiment...")
    results = await Evaluator.run_experiment_from_config(config=config)
    output_dir = log_to_file(results)
    if run:
        log_to_neptune(run, results, output_dir)

    log.info("Evaluation results saved under directory: %s", output_dir)


@hydra.main(config_path="config", config_name="retrieval", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    asyncio.run(bench(config))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
