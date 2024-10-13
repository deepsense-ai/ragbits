import asyncio
import logging
from pathlib import Path

import hydra
import neptune
from hydra.core.hydra_config import HydraConfig
from neptune.utils import stringify_unsupported
from omegaconf import DictConfig

from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.loaders import HuggingFaceDataLoader
from ragbits.evaluate.metrics import MetricSet
from ragbits.evaluate.pipelines import DocumentSearchEvaluationPipeline
from ragbits.evaluate.utils import save

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
    pipeline = DocumentSearchEvaluationPipeline(config)
    metrics = MetricSet()(config)

    evaluator = Evaluator(task="document_search")
    results = await evaluator.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metrics=metrics,
    )

    log.info("Evaluation finished. Saving results...")

    output_dir = Path(HydraConfig.get().runtime.output_dir)
    metrics_file = output_dir / "metrics.json"
    results_file = output_dir / "results.json"

    save(metrics_file, metrics=results["metrics"], time_perf=results["time_perf"])
    save(results_file, results=results["results"])

    log.info("Evaluation results saved under directory: %s", output_dir)

    if config.neptune.run:
        run = neptune.init_run(project=config.neptune.project)
        run["sys/tags"].add(config.setup.name)
        run["config"] = stringify_unsupported(config)
        run["evaluation/metrics"] = stringify_unsupported(results["metrics"])
        run["evaluation/time_perf"] = stringify_unsupported(results["time_perf"])
        run["evaluation/metrics.json"].upload(metrics_file.as_posix())
        run["evaluation/results.json"].upload(results_file.as_posix())


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
