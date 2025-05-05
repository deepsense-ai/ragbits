# How-To: Register custom components

Ragbits allows you to extend its functionality by adding custom implementations of various components, such as [`sources`][ragbits.core.sources.Source] or [`elements`][ragbits.document_search.documents.element.Element]. In most cases, you just need to import them directly in your code and use them, but in some cases, such as source ingest via CLI, you need to import them implictly to avoid errors.

To register your component classes, include their module paths in the `modules_to_import` section of your `pyproject.toml` file:

```toml
[tool.ragbits.core]
modules_to_import = [
    "python.path.to.custom_source",
    "python.path.to.custom_element",
    ...
]
```

And that's it, Ragbits always reads `pyproject.toml` every time you run it and imports modules from it, so you can be sure that your components will always be available in a runtime.

!!! tip
    It is a good practice to put all custom components in the `modules_to_import` section to avoid potential errors in the future.
