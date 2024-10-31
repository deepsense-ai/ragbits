import sys
import hydra
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.loaders import dataloader_factory
from ragbits.evaluate.metrics import metric_set_factory
from ragbits.evaluate.optimizer import Optimizer
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.evaluate.utils import log_optimization_to_file


module = sys.modules[__name__]


@hydra.main(config_path="config", config_name="optimization", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    dataloader = dataloader_factory(config.data)
    pipeline_class = get_cls_from_config(config.pipeline.type, module)
    metrics = metric_set_factory(config.metrics)

    optimization_cfg = OmegaConf.create({"direction": "maximize", "n_trials": 10})
    optimizer = Optimizer(cfg=optimization_cfg)
    configs_with_scores = optimizer.optimize(
        pipeline_class=pipeline_class,
        config_with_params=config.pipeline,
        metrics=metrics,
        dataloader=dataloader,
    )
    log_optimization_to_file(configs_with_scores)


if __name__ == "__main__":
    main()
