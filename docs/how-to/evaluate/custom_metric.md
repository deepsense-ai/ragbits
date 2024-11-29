# How to create custom Metric for Ragbits evaluation

`ragbits.evaluate` package provides the implementation of metrics that measure the quality of document search pipeline within `ragbits.evaluate.metrics.document_search`
on your data, however you are not limited to this. In order to implement custom ones for your specific use case you would need to inherit from `ragbits.evaluate.metrics.base.Metric`
abstract class and implement `compute` method.

Please find the example here:

```python
from pprint import pp as pprint
import tiktoken
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.metrics.base import Metric, MetricSet, ResultT
from omegaconf import OmegaConf


class TokenCountMetric(Metric):
    def compute(self, results: list[ResultT]) -> dict[str, float]:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = [len(encoding.encode(out.answer)) for out in results]
        return {"num_tokens": sum(num_tokens) / len(num_tokens)}


metrics = MetricSet(TokenCountMetric())

optimization_cfg = OmegaConf.create(
    {"direction": "minimize", "n_trials": 4, "max_retries_for_trial": 3}
)
optimizer = Optimizer(optimization_cfg)

optimized_params = OmegaConf.create(
    {
        "system_prompt_content": {
            "optimize": True,
            "choices": [
                "Be a friendly bot answering user questions. Be as concise as possible",
                "Be a silly bot answering user questions. Use as few tokens as possible",
                "Be informative and straight to the point",
                "Respond to user questions in as few words as possible",
            ],
        }
    }
)
configs_with_scores = optimizer.optimize(
    pipeline_class=RandomQuestionRespondPipeline,
    config_with_params=optimized_params,
    metrics=metrics,
    dataloader=dataloader,
)
pprint(configs_with_scores)
```