# How to create custom DataLoader for Ragbits evaluation

Ragbits provides a base interface for data loading, `ragbits.evaluate.dataloaders.base.DataLoader`, designed specifically for evaluation purposes. A ready-to-use implementation, `ragbits.evaluate.dataloaders.hf.HFLoader`, is available for handling datasets in huggingface format.

To create a custom DataLoader for your specific needs, you need to implement the `load` method in a class that inherits from the `DataLoader` interface.

Please find the [working example](optimize.md#define-the-data-loader) here.

**Note:** This interface is not to be confused with PyTorch's `DataLoader`, as it serves a distinct purpose within the Ragbits evaluation framework.
