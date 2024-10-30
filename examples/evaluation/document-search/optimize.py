
import hydra
from omegaconf import DictConfig

from ragbits.evaluate.loaders import dataloader_factory
from ragbits.evaluate.metrics import metric_set_factory
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline
from ragbits.evaluate.utils import log_optimization_to_file


@hydra.main(config_path="config", config_name="optimization", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    dataloader = dataloader_factory(config.data)
    pipeline_class = DocumentSearchPipeline
    metrics = metric_set_factory(config.metrics)

    optimizer = Optimizer()
    configs_with_scores = optimizer.optimize(
        pipeline_class=pipeline_class,
        config_with_params=config.pipeline,
        metrics=metrics,
        dataloader=dataloader,
        direction="maximize",
        n_trials=3,
    )
    log_optimization_to_file(configs_with_scores)


if __name__ == "__main__":
    main()
