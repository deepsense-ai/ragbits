import sys

from datasets import Dataset
from distilabel.pipeline import Pipeline
from distilabel.steps.base import Step
from omegaconf import DictConfig, OmegaConf

from ragbits.core.utils.config_handling import get_cls_from_config

module = sys.modules[__name__]


class DatasetGenerationPipeline:
    """A pipeline for dataset generation"""

    def __init__(self, config: DictConfig):
        self.config = config

    def __call__(self, corpus: list[str]) -> Dataset:
        """
        Generates a dataset from a corpus or list of topics
        Args:
            corpus: a corpus of information or list of topics
        Returns:
            dataset instance
        """
        dataset = Dataset.from_dict({self.config.input_name: corpus})
        with Pipeline(self.config.pipeline.name) as pipeline:
            tasks = self._parse_pipeline_steps()
            prev_task = None
            for task in tasks:
                if prev_task:
                    prev_task >> task
                prev_task = task
        distiset = pipeline.run(use_cache=False, dataset=dataset)
        result = distiset["default"]["train"]
        result = result.remove_columns(["distilabel_metadata", "model_name"])
        return result

    def _parse_pipeline_steps(self) -> list[Step]:
        tasks = []
        for task_config in self.config.pipeline.tasks:
            llm_config = task_config.llm
            llm_kwargs = OmegaConf.to_container(llm_config.kwargs)
            llm = get_cls_from_config(llm_config.provider_type, module)(**llm_kwargs)
            task_kwargs = {"llm": llm}
            if getattr(task_config, "kwargs", None):
                task_kwargs.update(OmegaConf.to_container(task_config.kwargs))
            task = get_cls_from_config(task_config.type, module)(**task_kwargs)
            tasks.append(task)
            if getattr(task_config, "filters", None):
                for filter_type in task_config.filters:
                    filter = get_cls_from_config(filter_type, module)(tasks[-1])
                    tasks.append(filter)
        return tasks
