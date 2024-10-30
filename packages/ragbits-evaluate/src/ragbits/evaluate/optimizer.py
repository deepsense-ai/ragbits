import asyncio
import optuna
from omegaconf import DictConfig, OmegaConf
from hydra.utils import instantiate

from typing import Type

from scipy.special import kwargs

from .evaluator import Evaluator
from .pipelines.base import EvaluationPipeline

from .loaders.base import DataLoader
from .metrics.base import MetricSet



class Optimizer:
    """
    Class for optimization
    """

    def optimize(self, config_with_params: DictConfig, dataloader: DataLoader, metrics: MetricSet, **kwargs):
        objective = lambda trial: self._objective(trial=trial, config_with_params=config_with_params, dataloader=dataloader, metrics=metrics)
        study = optuna.create_study(direction=kwargs.get("direction", "maximize"))
        study.optimize(objective, n_trials=kwargs.get("n_trials", 1))

    def _objective(self, pipeline_class: Type[EvaluationPipeline], trial: optuna.Trial, config_with_params: DictConfig, dataloader: DataLoader, metrics: MetricSet):
        updates = self._get_values_from_marked_params(cfg=config_with_params, trial=trial)
        config_for_trial = OmegaConf.merge(config_with_params, updates)
        pipeline = pipeline_class(config_for_trial)
        return self._score(pipeline=pipeline, dataloader=dataloader, metrics=metrics)

    def _score(self, pipeline: EvaluationPipeline, dataloader: DataLoader, metrics: MetricSet) -> float:
        if not isinstance(pipeline, EvaluationPipeline):
            raise ValueError("Defined class of pipeline should inherit from Evaluation Pipeline")
        evaluator = Evaluator()
        results = asyncio.run(evaluator.compute(
            pipeline=pipeline,
            dataloader=dataloader,
            metrics=metrics)
        )
        score = sum(results["metrics"]["metrics"].values())
        return score

    @staticmethod
    def _get_values_from_marked_params(cfg: DictConfig, trial: optuna.Trial, result: dict | None = None) -> DictConfig | str | float | int:
        """
        Returns a new dictionary with the keys that contain 'opt_params_range' replaced
        by random numbers between the specified range [A, B].
        """
        result = {}
        for key, value in cfg.items():
            if isinstance(value, DictConfig):
                nested_result = Optimizer._get_values_from_marked_params(value, trial, result)
                if nested_result:  # Only add if nested_result is not empty
                    result[key] = nested_result
            elif key == "opt_params_range":
                if isinstance(value[0], float) and isinstance(value[1], float):
                    res = trial.suggest_float(name=key, low=value[0], high=value[1])
                elif isinstance(value[0], int) and isinstance(value[1], int):
                    res = trial.suggest_int(name=key, low=value[0], high=value[1])
                else:
                    res = None
                return res
            elif key == "opt_params_values":
                res = trial.suggest_categorical(name=key, choices=value)
                return res  # Return single random value if opt_params_range is found
        return OmegaConf.create(result)

