import asyncio
import optuna
from omegaconf import DictConfig, OmegaConf

from typing import Type

from sympy.ntheory.factor_ import trial_msg

from .evaluator import Evaluator
from .pipelines.base import EvaluationPipeline

from .loaders.base import DataLoader
from .metrics.base import MetricSet


class Optimizer:
    """
    Class for optimization
    """

    def optimize(
        self,
        pipeline_class: Type[EvaluationPipeline],
        config_with_params: DictConfig,
        dataloader: DataLoader,
        metrics: MetricSet,
        **kwargs,
    ) -> list[tuple[DictConfig, float, dict[str, float]]]:
        objective = lambda trial: self._objective(
            trial=trial,
            pipeline_class=pipeline_class,
            config_with_params=config_with_params,
            dataloader=dataloader,
            metrics=metrics,
        )
        study = optuna.create_study(direction=kwargs.get("direction", "maximize"))
        study.optimize(objective, n_trials=kwargs.get("n_trials", 1))
        configs_with_scores = [(trial.user_attrs["cfg"], trial.user_attrs["score"], trial.user_attrs["all_metrics"]) for trial in study.get_trials()]
        return configs_with_scores

    def _objective(
        self,
        pipeline_class: Type[EvaluationPipeline],
        trial: optuna.Trial,
        config_with_params: DictConfig,
        dataloader: DataLoader,
        metrics: MetricSet,
    ) -> float:
        updates = self._get_pipeline_config_from_parametrized(cfg=config_with_params, trial=trial)
        config_for_trial = OmegaConf.merge(config_with_params, updates)
        pipeline = pipeline_class(config_for_trial)
        metrics_values = self._score(pipeline=pipeline, dataloader=dataloader, metrics=metrics)
        score = sum(metrics_values.values())
        trial.set_user_attr("score", score)
        trial.set_user_attr("cfg", config_for_trial)
        trial.set_user_attr("all_metrics", metrics_values)
        return score

    def _score(self, pipeline: EvaluationPipeline, dataloader: DataLoader, metrics: MetricSet) -> dict[str, float]:
        evaluator = Evaluator()
        event_loop = asyncio.new_event_loop()
        # AFAIR optuna does not support async objective functions
        results = event_loop.run_until_complete(evaluator.compute(pipeline=pipeline, dataloader=dataloader, metrics=metrics))
        return results["metrics"]

    @staticmethod
    def _get_pipeline_config_from_parametrized(
        cfg: DictConfig, trial: optuna.Trial, result: dict | None = None
    ) -> DictConfig | str | float | int:
        """
        Returns a new dictionary with the keys that contain 'opt_params_range' replaced
        by random numbers between the specified range [A, B].
        """
        result = {}
        for key, value in cfg.items():
            if isinstance(value, DictConfig):
                nested_result = Optimizer._get_pipeline_config_from_parametrized(value, trial, result)
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
