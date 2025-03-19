# Create custom Evaluation Pipeline

Ragbits provides a ready-to-use evaluation pipeline for document search, implemented within the `ragbits.evaluate.document_search.DocumentSearchPipeline` module.

To create a custom evaluation pipeline for your specific use case, you need to implement the `__call__` method as part of the `ragbits.evaluate.pipelines.base.EvaluationPipeline` interface.


Please find the [working example](optimize.md#define-the-optimized-pipeline-structure) here