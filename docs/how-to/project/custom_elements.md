# How-To: Register custom sources and elements in Ragbits

## Introduction
Ragbits allows you to extend its functionality by adding your own custom sources and elements. This guide shows how to define and register these extensions so they are automatically available throughout your project.

## Custom sources
To create a custom source, refer to [this](../sources/load-dataset.md#custom-source) guide.

To register your custom source class update `pyproject.toml` within your project root with the following lines:

```toml
[tool.ragbits.core]
modules_to_import = ["python.path.to.custom_source"]
```

You can specify any number of modules in that list — all source classes found in those modules will be imported and registered automatically.

## Custom elements

To define a new element, extend the [`Element`][ragbits.document_search.documents.element.Element] class. Here's a basic template for a custom element class:

```python
class CustomElement(Element):
    element_type: str = "custom_element"
    custom_field: str

    @computed_field
    @property
    def text_representation(self) -> str:
        return self.custom_field
```

### Registering custom elements

To register your custom element classes, include their module paths in the `modules_to_import` section of your `pyproject.toml` file:

```toml
[tool.ragbits.core]
modules_to_import = [
    "python.path.to.custom_source",
    "python.path.to.custom_element",
]
```

This setup allows you to register both custom sources and custom elements in one place, making your extensions automatically available throughout the system.