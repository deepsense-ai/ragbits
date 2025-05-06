# How-To: Evaluate pipelines with Ragbits

Ragbits provides an interface for evaluating pipelines using specified metrics. Generally, you can create any evaluation pipeline and metrics that comply with the interface.

Before running the evaluation, ensure the following prerequisites are met:

1. Define the `EvaluationPipeline` structure class ([Example](optimize.md#define-the-optimized-pipeline-structure))
2. Define the `Metrics` and organize them into a `MetricSet` ([Example](optimize.md#define-the-metrics))
3. Define the `DataLoader` ([Example](optimize.md#define-the-data-loader))

## Running evaluation from source code

The evaluation example is very similar to the one used in [optimization](optimize.md), and it utilizes the same implementations of the required classes.
The only difference is in the structure of the configuration file, as it does not need to include optimizer options or the parameters to be optimized.

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

After the successful execution, your console should print a dictionary with keys corresponding to components of each metric and values
equal to results aggregated over the defined dataloader.

## Running evaluation from CLI

Ragbits CLI provides a command to run evaluation in convenient way from the command line:

```bash
ragbits evaluate run \
    --dataloader-factory-path TEXT  # Factory path for data loader (python.path:ModuleName) [default: None] \
    --dataloader-yaml-path PATH     # YAML config file path for data loader [default: None] \
    --target-factory-path TEXT      # Factory path for target (python.path:function_name) [default: None] \
    --target-yaml-path PATH         # YAML config file path for target [default: None] \
    --metrics-factory-path TEXT     # Factory path for metrics (python.path:function_name) [default: None] \
    --metrics-yaml-path PATH        # YAML config file path for metrics [default: None]
```

!!! notes
    * The `--target-factory-path` and `--target-yaml-path` are interchangeable, as are `--metrics-factory-path` and `--metrics-yaml-path`.
    Use one or the other based on your configuration preference.
    * Non-required parameters (those with [default: None]) will be sourced from the project configuration if not provided.

Example command:

```bash
ragbits evaluate \
  --dataloader-factory-path ragbits.evaluate.factories:synthetic_rag_dataset \
  --target-factory-path ragbits.evaluate.factories:basic_document_search_factory \
  --metrics-factory-path ragbits.evaluate.factories:precision_recall_f1 \
  run
```
