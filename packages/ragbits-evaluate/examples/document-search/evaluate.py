import asyncio
import logging
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.loaders import HuggingFaceDataLoader
from ragbits.evaluate.metrics import DocumentSearchPrecision, DocumentSearchRecall, MetricSet
from ragbits.evaluate.metrics.document_search import DocumentSearchF1
from ragbits.evaluate.pipelines import DocumentSearchPipeline
from ragbits.evaluate.utils import log_to_file, log_to_neptune

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


async def bench(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    log.info("Starting evaluation: %s", config.setup.name)

    dataloader = HuggingFaceDataLoader(config)
    pipeline = DocumentSearchPipeline(config)
    metrics = MetricSet(
        DocumentSearchPrecision,
        DocumentSearchRecall,
        DocumentSearchF1,
    )(config)

    evaluator = Evaluator()
    results = await evaluator.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metrics=metrics,
    )

    log.info("Evaluation finished. Saving results...")

    output_dir = Path(HydraConfig.get().runtime.output_dir)
    log_to_file(results, output_dir)

    if config.neptune.run:
        log_to_neptune(config, results, output_dir)

    log.info("Evaluation results saved under directory: %s", output_dir)


@hydra.main(config_path="config", config_name="config", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    asyncio.run(bench(config))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
