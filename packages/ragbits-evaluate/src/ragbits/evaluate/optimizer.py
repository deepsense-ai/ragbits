import asyncio
import optuna
import json
from omegaconf import DictConfig, ListConfig, OmegaConf
from copy import deepcopy

from typing import Any, Type

from .evaluator import Evaluator
from .pipelines.base import EvaluationPipeline

from .loaders.base import DataLoader
from .metrics.base import MetricSet


def _is_json_string(string: str) -> bool:
    try:
        _ = json.loads(string)
        return True
    except json.decoder.JSONDecodeError:
        return False

class Optimizer:
    """
    Class for optimization
    """
    def __init__(self, cfg: DictConfig):
        self.config = cfg
        # workaround for optuna not allowing different choices for different trials
        self._choices_cache: dict[str, list[Any]] = {}

    def optimize(
        self,
        pipeline_class: Type[EvaluationPipeline],
        config_with_params: DictConfig,
        dataloader: DataLoader,
        metrics: MetricSet,
    ) -> list[tuple[DictConfig, float, dict[str, float]]]:
        objective = lambda trial: self._objective(
            trial=trial,
            pipeline_class=pipeline_class,
            config_with_params=config_with_params,
            dataloader=dataloader,
            metrics=metrics,
        )
        study = optuna.create_study(direction=self.config.direction)
        study.optimize(objective, n_trials=self.config.n_trials)
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
        config_for_trial = deepcopy(config_with_params)
        self._set_values_for_optimized_params(cfg=config_for_trial, trial=trial, ancestors=[])
        pipeline = pipeline_class(config_for_trial)
        metrics_values = self._score(pipeline=pipeline, dataloader=dataloader, metrics=metrics)
        score = sum(metrics_values.values())
        trial.set_user_attr("score", score)
        trial.set_user_attr("cfg", config_for_trial)
        trial.set_user_attr("all_metrics", metrics_values)
        return score

    def _score(self, pipeline: EvaluationPipeline, dataloader: DataLoader, metrics: MetricSet) -> dict[str, float]:
        evaluator = Evaluator()
        event_loop = asyncio.get_event_loop()
        # AFAIR optuna does not support async objective functions
        results = event_loop.run_until_complete(evaluator.compute(pipeline=pipeline, dataloader=dataloader, metrics=metrics))
        return results["metrics"]

    def _set_values_for_optimized_params(self, cfg: DictConfig, trial: optuna.Trial, ancestors: list[str]) -> None:
        """
        Modifies the original dictionary in place, replacing values for keys that contain
        'opt_params_range' with random numbers between the specified range [A, B] or for
        'opt_params_values' with a choice from a provided list of values.
        """
        for key, value in cfg.items():
            if isinstance(value, DictConfig):
                if value.get("optimize"):
                    param_id = f"{'.'.join(ancestors)}.{key}"
                    choices = self._choices_cache.get(param_id) or value.get("choices")
                    range = value.get("range")
                    assert not (choices and range), "Choices and range cannot be defined in couple"
                    if range:
                        if isinstance(range[0], float) and isinstance(range[1], float):
                            cfg[key] = trial.suggest_float(name=param_id, low=range[0], high=range[1])
                        elif isinstance(range[0], int) and isinstance(range[1], int):
                            cfg[key] = trial.suggest_int(name=param_id, low=range[0], high=range[1])
                    else:
                        assert choices, "Either choices or range must be specified"
                        if isinstance(choices[0], DictConfig):
                            choices = [json.dumps(OmegaConf.to_container(ch)) for ch in choices]
                        self._choices_cache[param_id] = choices
                        choice = trial.suggest_categorical(name=param_id, choices=choices)
                        choice = OmegaConf.create(json.loads(choice)) if _is_json_string(choice) else choice
                        if isinstance(choice, DictConfig):
                            self._set_values_for_optimized_params(choice, trial, ancestors + [key])
                        cfg[key] = choice
                else:
                    self._set_values_for_optimized_params(value, trial, ancestors + [key])
            elif isinstance(value, ListConfig):
                for param in value:
                    if isinstance(param, DictConfig):
                        self._set_values_for_optimized_params(param, trial, ancestors + [key])



