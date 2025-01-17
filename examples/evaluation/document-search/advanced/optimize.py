import logging
from typing import cast

import hydra
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.utils import log_optimization_to_file

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


@hydra.main(config_path="config", config_name="optimization", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Runs the optimization process.

    Args:
        config: Hydra configuration.
    """
    print("Starting optimization...")

    optimizer_config = cast(dict, OmegaConf.to_container(config))
    configs_with_scores = Optimizer.run_from_config(optimizer_config)

    output_dir = log_optimization_to_file(configs_with_scores)
    print(f"Optimization results saved under directory: {output_dir}")


if __name__ == "__main__":
    main()
