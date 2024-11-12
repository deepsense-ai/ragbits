import hydra
from omegaconf import DictConfig

from ragbits.evaluate.dataset_generator.pipeline import DatasetGenerationPipeline
from ragbits.evaluate.utils import log_dataset_to_file


@hydra.main(config_path="config", config_name="generate", version_base="3.2")
def main(config: DictConfig):
    TOPICS = ["conspiracy theories", "machine learning"]

    generation_pipeline = DatasetGenerationPipeline(config=config)
    result_dataset = generation_pipeline(corpus=TOPICS)
    breakpoint()
    log_dataset_to_file(dataset=result_dataset)


if __name__ == "__main__":
    main()
