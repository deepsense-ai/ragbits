# How-To: Autoconfigure your pipeline

Ragbits offers a feature enabling users to automatically configure the hyperparameters of the pipeline.

The functionality is agnostic of a type of optimized structure - the only assumptions are:is that it needs to inherit

* the optimized pipeline structure needs to inherit from `ragbits.evaluate.pipelines.base.EvaluationPipeline`
* definition of optimized metrics need to follow `ragbits.evaluate.metrics.base.Metric` interface
* they need to be gathered into `ragbits.evaluate.metrics.base.MetricSet` object instance



## Supported parameter types

The optimize parameters can be:

* continous
* ordinal
* categorical


Ordinal and continous ones need to be primitives, for categorical - the more sophisticated structures
which can also include nested parameters of other types are supported.


## Usage

You need to create an instance of a class `ragbits.evaluate.Optimizer`, and pass it:

* `pipeline_class` - a type of object to be optimized
* `config_with_params` - `omegaconf.DictConfig` - a definition of configuration
*

