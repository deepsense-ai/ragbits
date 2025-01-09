import sys
from typing import cast

import hydra
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.utils import log_optimization_to_file

module = sys.modules[__name__]


@hydra.main(config_path="config", config_name="optimization", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    exp_config = {
        "optimizer": {"direction": "maximize", "n_trials": 10},
        "experiment_config": cast(dict, OmegaConf.to_container(config)),
    }
    configs_with_scores = Optimizer.run_experiment_from_config(config=exp_config)
    log_optimization_to_file(configs_with_scores)


if __name__ == "__main__":
    main()
