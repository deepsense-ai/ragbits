"""
Ragbits Evaluate Example: Dataset Generation

This example demonstrates how to generate a synthetic dataset using the `DatasetGenerationPipeline` class.
It uses Hydra for configuration management and allows specifying topics for dataset generation.
The generated dataset is then logged to a file.

To run the script, execute the following command:

    ```bash
    uv run examples/evaluate/dataset-generator/generate.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-document-search",
#     "ragbits-evaluate",
# ]
# ///

import hydra
from omegaconf import DictConfig

from ragbits.evaluate.dataset_generator.pipeline import DatasetGenerationPipeline
from ragbits.evaluate.utils import log_dataset_to_file


@hydra.main(config_path="config", config_name="generate", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    A main function for dataset generation example
    Args:
        config (DictConfig) - configuration should follow
        ragbits.evaluate.dataset_generator.DatasetGenerationPipelineConfig data model
    Returns:
        None
    """
    TOPICS = ["conspiracy theories", "machine learning"]
    generation_pipeline = DatasetGenerationPipeline.from_dict_config(dict_config=config)
    result_dataset = generation_pipeline(corpus=TOPICS)
    log_dataset_to_file(dataset=result_dataset)


if __name__ == "__main__":
    main()
