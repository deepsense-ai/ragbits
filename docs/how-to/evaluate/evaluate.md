# How to Evaluate with Ragbits

Ragbits provides an interface for evaluating pipelines using specified metrics. Generally, you can create any evaluation pipeline and metrics that comply with the interface.

Before running the evaluation, ensure the following prerequisites are met:

1. Define the `EvaluationPipeline` structure class ([Example](optimize.md#define-the-optimized-pipeline-structure))
2. Define the `Metrics` and organize them into a `MetricSet` ([Example](optimize.md#define-the-metrics-and-run-the-experiment))
3. Define the `DataLoader` ([Example](optimize.md#define-the-data-loader))

The evaluation interface is very similar to the one used in [optimization](optimize.md) though we would use the same implementations
of required classes - the only difference is a structure of the configuration file as it does not need to define optimizer options and
parameters to be optimized.

```python
import asyncio
from ragbits.evaluate.evaluator import Evaluator


async def main():
    config = {
        "dataloader": {
            "type": f"{__name__}:RandomQuestionsDataLoader",
            "config": {"num_questions": 10, "question_topic": "conspiracy theories"},
        },
        "pipeline": {
            "type": f"{__name__}:RandomQuestionRespondPipeline",
            "config": {
                "system_prompt_content":  "Respond to user questions in as few words as possible"
                }
            },
        "metrics": {
            "precision_recall_f1": {
                "type": f"{__name__}:TokenCountMetric",
                "config": {},
            },
        },
    }
    results = await Evaluator.run_from_config(config=config)
    return results

asyncio.run(main())
```

After the succesful execution your console should print a dictionary with keys corresponding to components of each metric and values
equal to results aggregated over the defined dataloader.