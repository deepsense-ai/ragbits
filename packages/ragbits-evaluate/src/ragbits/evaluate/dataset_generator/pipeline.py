import sys
from typing import Any

from datasets import Dataset
from distilabel.pipeline import Pipeline
from distilabel.steps.base import Step
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel

from ragbits.core.utils.config_handling import import_by_path

module = sys.modules[__name__]


class LLMConfigForTask(BaseModel):
    """
    Configuration for the LLM (Language Model) associated with a specific task.

    Attributes:
        provider_type (str): The type of LLM provider.
        kwargs (dict): Additional parameters or settings for the LLM provider.
    """

    provider_type: str
    kwargs: dict


class TaskConfig(BaseModel):
    """
    Configuration for an individual task in the dataset generation pipeline.

    Attributes:
        type: str: type of the task
        llm (LLMConfigForTask): The configuration for the LLM used in this task.
        kwargs (dicts): Optional additional parameters or settings for the task.
        filters (list[str] | None): Optional filters to apply during the task. Defaults to None.
    """

    type: str
    llm: LLMConfigForTask
    kwargs: dict | None = None
    filters: list[str] | None = None


class DatasetGenerationPipelineConfig(BaseModel):
    """
    Configuration for the entire dataset generation pipeline.

    Attributes:
        name (str): The name of the dataset generation pipeline.
        input_name (str): The name of the input resource or dataset.
        tasks (list[TaskConfig]): A list of task configurations included in the pipeline.
    """

    name: str
    input_name: str
    tasks: list[TaskConfig]

    @classmethod
    def from_dict_config(cls, dict_config: DictConfig) -> "DatasetGenerationPipelineConfig":
        """
        Creates an instance of `DatasetGenerationPipelineConfig` from a dictionary-based configuration.

        Args:
            dict_config (DictConfig): A configuration object containing pipeline details.

        Returns:
            DatasetGenerationPipelineConfig: An instance populated with data from the given configuration.

        """
        name = dict_config.name
        input_name = dict_config.input_name
        tasks = [
            TaskConfig(
                type=task_config.type,
                llm=LLMConfigForTask(
                    provider_type=task_config.llm.provider_type,
                    kwargs=OmegaConf.to_container(task_config.llm.kwargs),  # type: ignore
                ),
                kwargs=OmegaConf.to_container(task_config.kwargs),  # type: ignore
                filters=getattr(task_config, "filters", None),
            )
            for task_config in dict_config.tasks
        ]
        return cls(name=name, input_name=input_name, tasks=tasks)


class DatasetGenerationPipeline:
    """A pipeline for dataset generation"""

    def __init__(self, config: DatasetGenerationPipelineConfig):
        self.config = config
        self._instantiate_pipeline()

    @classmethod
    def from_dict_config(cls, dict_config: DictConfig) -> "DatasetGenerationPipeline":
        """
        Instantiates the pipeline from dict config validated through pydantic base model
        Returns:
            DatasetGenerationPipeline
        """
        config = DatasetGenerationPipelineConfig.from_dict_config(dict_config=dict_config)
        return cls(config=config)

    def __call__(self, corpus: list[str]) -> Dataset:
        """
        Generates a dataset from a corpus or list of topics
        Args:
            corpus: a corpus of information or list of topics
        Returns:
            dataset instance
        """
        dataset = Dataset.from_dict({self.config.input_name: corpus})
        distiset = self.pipeline.run(use_cache=False, dataset=dataset)
        result = distiset["default"]["train"]
        result = result.remove_columns(["distilabel_metadata", "model_name"])
        return result

    def _parse_pipeline_steps(self) -> list[Step]:
        tasks = []
        for task_config in self.config.tasks:
            llm_config = task_config.llm
            llm = import_by_path(llm_config.provider_type, module)(**llm_config.kwargs)
            task_kwargs: dict[Any, Any] = {"llm": llm}
            task_kwargs.update(task_config.kwargs or {})  # type: ignore
            task = import_by_path(task_config.type, module)(**task_kwargs)
            tasks.append(task)
            filter_types = getattr(task_config, "filters", None) or []
            for filter_type in filter_types:
                filter = import_by_path(filter_type, module)(tasks[-1])
                tasks.append(filter)
        return tasks

    def _instantiate_pipeline(self) -> None:
        with Pipeline(self.config.name) as self.pipeline:
            tasks = self._parse_pipeline_steps()
            prev_task = None
            for task in tasks:
                if prev_task:
                    prev_task >> task
                prev_task = task
