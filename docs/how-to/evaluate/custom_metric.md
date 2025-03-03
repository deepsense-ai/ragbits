# How to create custom Metric for Ragbits evaluation

`ragbits.evaluate` package provides the implementation of metrics that measure the quality of document search pipeline within `ragbits.evaluate.metrics.document_search`
on your data, however you are not limited to this. In order to implement custom ones for your specific use case you would need to inherit from `ragbits.evaluate.metrics.base.Metric`
abstract class and implement `compute` method.

Please find the [working example](optimize.md#define-the-metrics) here.