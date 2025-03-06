# How to Set Preferred Components for Your Project

## Introduction
When you use Ragbits in your project, you can set the preferred components for different component types (like embedders, vector stores, LLMs, etc.) in the project configuration. Typically, there are many different implementations for each type of component, and each implementation has its own configuration. Ragbits allows you to choose the implementation you prefer for each type of component and the configuration to be used along with it.

In this guide, you will learn two methods of setting the preferred components for your project: [by a factory function](#by-a-factory-function) and [by a YAML configuration file](#by-a-yaml-configuration-file). Preferred components are used automatically by the [Ragbits CLI](../../cli/main.md), and you will also learn [how to use them in your own code](#using-the-preferred-components). At the end of the guide, you will find a [list of component types](#list-of-component-types) for which you can set the preferred configuration.

## Setting the Preferred Components
You can specify the component preferences in two different ways: either by providing a factory function that creates the preferred instance of the component or by providing a YAML configuration file that contains the preferred configuration.

### By a Factory Function
To set the preferred component using a factory function, you need to create a function that takes no arguments and returns an instance of the component. You then set the full Python path to this function in the `[tool.ragbits.core.component_preference_factories]` section of your project's `pyproject.toml` file.

For example, to designate `QdrantVectorStore` (with an in-memory `AsyncQdrantClient`) as the preferred vector store implementation, you can create a factory function like this:

```python
from ragbits.core.vector_stores import QdrantVectorStore
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from qdrant_client import AsyncQdrantClient

def get_qdrant_vector_store():
    return QdrantVectorStore(
        client=AsyncQdrantClient(location=":memory:"),
        index_name="my_index",
        embedder=LiteLLMEmbedder(),
    )
```

Then, you set the full Python path to this function in the `[tool.ragbits.core.component_preference_factories]` section of your project's `pyproject.toml` file:

```toml
[tool.ragbits.core.component_preference_factories]
vector_store = "my_project.get_qdrant_vector_store"
```

The key `vector_store` is the name of the component type for which you are setting the preferred configuration. To see all possible component types, refer to the [List of Component Types](#list-of-component-types) section below. The `[tool.ragbits.core.component_preference_factories]` may contain multiple keys, each corresponding to a different component type. For example:

```toml
[tool.ragbits.core.component_preference_factories]
vector_store = "my_project.get_qdrant_vector_store"
embedder = "my_project.get_litellm_embedder"
```

<a name="llm-configuration"></a>
!!! info "LLM Specific Configuration"
    Ragbits can distinguish between LLMs, depending on their capabilities. You can use a special `[tool.ragbits.core.llm_preference_factories]` section in your `pyproject.toml` file to set the preferred LLM factory functions for different types of LLMs. For example:

    ```toml
    [tool.ragbits.core.llm_preference_factories]
    text = "my_project.get_text_llm"
    vision = "my_project.get_vision_llm"
    structured_output = "my_project.get_structured_output_llm"
    ```

    The keys in the `[tool.ragbits.core.llm_preference_factories]` section are the names of the LLM types for which you are setting the preferred configuration. The possible LLM types are `text`, `vision`, and `structured_output`. The values are the full Python paths to the factory functions that create instances of the LLMs.

### By a YAML Configuration File
To set the preferred components using a YAML configuration file, you need to create a YAML file that contains the preferred configuration for different types of components. You then set the path to this file in the `[tool.ragbits.core]` section of your project's `pyproject.toml` file.

For example, to designate `QdrantVectorStore` (with an in-memory `AsyncQdrantClient`) as the preferred vector store implementation, you can create a YAML file like this:

```yaml
vector_store:
  type: QdrantVectorStore
  config:
    client:
      location: ":memory:"
    index_name: my_index
    embedder:
      type: LiteLLMEmbedder
```

Then, you set the path to this file as `component_preference_config_path` in the `[tool.ragbits.core]` section of your project's `pyproject.toml` file:

```toml
[tool.ragbits.core]
component_preference_config_path = "preferred_instances.yaml"
```

Each key in the YAML configuration file corresponds to a different [component type](#list-of-component-types). The value of each key is a dictionary with up to two keys: `type` and `config`. The `type` key is the name of the preferred component implementation, and the optional `config` key is the configuration to be used with the component. The configuration is specific to each component type and implementation and corresponds to the arguments of the component's constructor.

When using subclasses built into Ragbits, you can use either the name of the class alone (like the `QdrantVectorStore` in the example above) or the full Python path to the class (like `ragbits.core.vector_stores.QdrantVectorStore`). For other classes (like your own custom implementations of Ragbits components), you must use the full Python path.

In the example, the `vector_store` key is the name of the component type for which you are setting the preferred component. To see all possible component types, refer to the [List of Component Types](#list-of-component-types). The YAML configuration may contain multiple keys, each corresponding to a different component type. For example:

```yaml
vector_store:
  type: QdrantVectorStore
  config:
    client:
      location: ":memory:"
    index_name: my_index
    embedder:
      type: LiteLLMEmbedder

rephraser:
  type: NoopQueryRephraser
```

<a name="ds-configuration"></a>
!!! info "`DocumentSearch` Specific Configuration"
    While you can provide `DocumentSearch` with a preferred configuration in the same way as other components (by setting the `document_search` key in the YAML configuration file), there is also a shortcut. If you don't provide a preferred configuration for `DocumentSearch` explicitly, it will look for your project's preferences regarding all the components that `DocumentSearch` needs (like `vector_store`, `provider`, `rephraser`, `reranker`, etc.) and create a `DocumentSearch` instance with your preferred components. This way, you don't have to configure those components twice (once for `DocumentSearch` and once for the component itself).

    This is an example of a YAML configuration file that sets the preferred configuration for `DocumentSearch` explicitly:

    ```yaml
    document_search:
      type: DocumentSearch
      config:
        rephraser:
          type: NoopQueryRephraser
        vector_store:
          type: InMemoryVectorStore
          config:
            embedder:
              type: NoopEmbedder
    ```

    This is an example of a YAML configuration file that sets the preferred configuration for `DocumentSearch` implicitly:

    ```yaml
    rephraser:
      type: NoopQueryRephraser
    vector_store:
      type: InMemoryVectorStore
      config:
        embedder:
          type: NoopEmbedder
    ```

    In both cases, `DocumentSearch` will use `NoopEmbedder` as the preferred embedder and `InMemoryVectorStore` as the preferred vector store.

## Using the Preferred Components
Preferred components are used automatically by the [Ragbits CLI](../../cli/main.md). The `ragbits` commands that work on components (like [`ragbits vector-store`](../../cli/main.md#ragbits-vector-store), [`ragbits document-search`](../../cli/main.md#ragbits-document-search), etc.) will use the component preferred for the given type unless instructed otherwise.

You can also retrieve preferred components in your own code by instantiating the component using the `preferred_subclass()` factory method of [the base class of the given component type](#list-of-component-types). This method will automatically create an instance of the preferred implementation of the component with the configuration you have set.

For example, the code below will create an instance of the default vector store implementation with the default configuration (as long as you have [set the default vector store in the project configuration](#how-to-set-preferred-components-for-your-project)):

```python
from ragbits.core.vector_stores import VectorStore

vector_store = VectorStore.preferred_subclass()
```

Note that `VectorStore` itself is an abstract class, so the instance created by `preferred_subclass()` will be an instance of one of the concrete subclasses of `VectorStore` that you have set as the preferred in the project configuration.

<a name="llm-usage"></a>
!!! note "LLM Specific Usage"
    If you [set the preferred LLM factory functions](#llm-configuration) in the project configuration, you can use the `get_preferred_llm()` function to create an instance of the preferred LLM for a given type. For example:

    ```python
    from ragbits.core.llms.factory import get_preferred_llm, LLMType

    text_llm = get_preferred_llm(LLMType.TEXT)  # one of: TEXT, VISION, STRUCTURED_OUTPUT
    ```

### List of Component Types
This is the list of component types for which you can set a preferred configuration:

| Key                  | Package                   | Base class                                        | Notes                                        |
|----------------------|---------------------------|---------------------------------------------------|----------------------------------------------|
| `embedder`           | `ragbits-core`            | [`Embedder`][ragbits.core.embeddings.Embedder]    |                                              |
| `llm`                | `ragbits-core`            | [`LLM`][ragbits.core.llms.LLM]                    | Specifics: [Configuration](#llm-configuration), [Usage](#llm-usage)|
| `vector_store`       | `ragbits-core`            | [`VectorStore`][ragbits.core.vector_stores.base.VectorStore]|                                          |
| `history_compressor` | `ragbits-conversations`   | [`ConversationHistoryCompressor`][ragbits.conversations.history.compressors.base.ConversationHistoryCompressor]|          |
| `document_search`    | `ragbits-document-search` | [`DocumentSearch`][ragbits.document_search.DocumentSearch]| Specifics: [Configuration](#ds-configuration)|
| `provider`           | `ragbits-document-search` | [`BaseProvider`][ragbits.document_search.ingestion.providers.base.BaseProvider]|                                              |
| `rephraser`          | `ragbits-document-search` | [`QueryRephraser`][ragbits.document_search.retrieval.rephrasers.QueryRephraser]|                                          |
| `reranker`           | `ragbits-document-search` | [`Reranker`][ragbits.document_search.retrieval.rerankers.base.Reranker]|                                               |
