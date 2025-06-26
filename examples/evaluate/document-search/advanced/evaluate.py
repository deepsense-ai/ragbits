"""
Ragbits Evaluate Example: Advanced Document Search Evaluation

This example demonstrates how to evaluate an advanced document search pipeline using the `Evaluator` class.
It uses Hydra for configuration management to define the evaluation process.

To run the script, execute the following commands:

    ```bash
    # default settings:
    uv run examples/evaluate/document-search/advanced/evaluate.py

    # custom settings:
    uv run examples/evaluate/document-search/advanced/evaluate.py +experiments=chunking-250

    # multirun with custom settings:
    uv run examples/evaluate/document-search/advanced/evaluate.py --multirun +experiments=chunking-250,chunking-500,chunking-1000

    # local logging:
    uv run examples/evaluate/document-search/advanced/evaluate.py logger.local=True

    # Neptune logging:
    uv run examples/evaluate/document-search/advanced/evaluate.py logger.neptune=True
    ```
"""  # noqa: E501

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[chroma,hf]",
#     "ragbits-document-search[unstructured]",
#     "ragbits-evaluate[relari]",
#     "unstructured[md]>=0.16.9,<1.0.0",
# ]
# ///

import asyncio
import logging
from typing import cast

import hydra
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.utils import log_evaluation_to_file, log_evaluation_to_neptune

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


async def evaluate(config: DictConfig) -> None:
    """
    Document search evaluation runner.

    Args:
        config: Hydra configuration.
    """
    print("Starting evaluation...")

    evaluator_config = cast(dict, OmegaConf.to_container(config))
    results = await Evaluator.run_from_config(evaluator_config)

    if config.logger.local:
        output_dir = log_evaluation_to_file(results)
        print(f"Evaluation results saved under directory: {output_dir}")

    if config.logger.neptune:
        log_evaluation_to_neptune(results, config)
        print("Evaluation results uploaded to Neptune")


@hydra.main(config_path="config", config_name="retrieval", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Runs the evaluation process.

    Args:
        config: Hydra configuration.
    """
    asyncio.run(evaluate(config))


if __name__ == "__main__":
    main()
