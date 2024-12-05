# How to Evaluate with Ragbits

Ragbits provides an interface for evaluating pipelines using specified metrics. Generally, you can create any evaluation pipeline and metrics that comply with the interface.

Before running the evaluation, ensure the following prerequisites are met:

1. Define the `EvaluationPipeline` structure class ([Example](optimize.md#define-the-optimized-pipeline-structure))
2. Define the `Metrics` and organize them into a `MetricSet` ([Example](optimize.md#define-the-metrics-and-run-the-experiment))
3. Define the `DataLoader` ([Example](optimize.md#define-the-data-loader))

The evaluator interface itself is straightforward and requires no additional configuration to instantiate. Once the three prerequisites are complete, running the evaluation is as simple as:


```python
import asyncio
from omegaconf import OmegaConf
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet




async def main():
    pipeline_config = OmegaConf.create({...})
    pipeline = YourPipelineClass(config=pipeline_config)

    metrics = [SomeMetric(OmegaConf.create({...})) for SomeMetric in your_metrics]
    metric_set = MetricSet(*metrics)

    dataloader = YourDataLoaderClass(OmegaConf.create({...}))

    evaluator = Evaluator()

    eval_results = await evaluator.compute(pipeline=pipeline, metrics=metric_set, dataloader=dataloader)
    print(eval_results)

asyncio.run(main())
```

After the succesful execution your console should print a dictionary with keys corresponding to components of each metric and values
equal to results aggregated over the defined dataloader.