import sys
from distilabel.pipeline import Pipeline
from distilabel.steps.base import Step
from omegaconf import DictConfig
from datasets import Dataset
from ragbits.core.utils.config_handling import get_cls_from_config

module = sys.modules[__name__]


class DatasetGenerationPipeline:
    def __init__(self, config: DictConfig):
        self.config = config

    def __call__(self, corpus: list[str]) -> Dataset:
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
            provider_type = llm_config.provider_type
            if provider_type.startswith("distilabel"):
                llm_kwargs = {"model": llm_config.name}
            elif provider_type.startswith("ragbits"):
                llm_kwargs = {"model_name": llm_config.name}
            llm = get_cls_from_config(llm_config.provider_type, module)(**llm_kwargs)
            task_kwargs = {"llm": llm, "num_per_query": getattr(task_config, "num_per_query", 1)}
            task = get_cls_from_config(task_config.type, module)(**task_kwargs)
            tasks.append(task)
            if getattr(task_config, "filter", None):
                filter = get_cls_from_config(task_config.filter, module)(task)
                tasks.append(filter)
        return tasks
