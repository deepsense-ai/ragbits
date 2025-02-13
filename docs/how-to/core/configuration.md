# How to Set Default Configuration for Components

## Introduction
When you use Ragbits in your project, you can set default configurations for different types of components (like embedders, vector stores, LLMs, etc.) in the project configuration. Typically, there are many different implementations for each type of component, and each implementation has its own configurations. Ragbits allows you to choose the implementation you want to use by default for each type of component and set configurations to be used along with it.

In this guide, you will learn two methods of setting the default components for your project: [by a factory function](#by-a-factory-function) and [by a YAML configuration file](#by-a-yaml-configuration-file). Your project's default components are used automatically by the [Ragbits CLI](../../cli/main.md), and you will also learn [how to use them in your own code](#using-the-default-components). At the end of the guide, you will find a [list of component types](#list-of-component-types) for which you can set the default implementation.

## Setting the Default Configuration
You can specify project's default configuration for components in two different ways: either by providing a factory function that creates the default instance of the component or by providing a YAML configuration file that contains the default configuration.

### By a Factory Function
To set the default configuration for a component using a factory function, you need to create a function that takes no arguments and returns an instance of the component. You then set the full Python path to this function in the `[tool.ragbits.core.default_factories]` section of your project's `pyproject.toml` file.

For example, to designate `QdrantVectorStore` (with an in-memory `AsyncQdrantClient`) as the default vector store implementation, you can create a factory function like this:

```python
from ragbits.core.vector_stores import QdrantVectorStore
from qdrant_client import AsyncQdrantClient

def get_qdrant_vector_store():
    return QdrantVectorStore(
        client=AsyncQdrantClient(location=":memory:"),
        index_name="my_index",
    )
```

Then, you set the full Python path to this function in the `[tool.ragbits.core.default_factories]` section of your project's `pyproject.toml` file:

```toml
[tool.ragbits.core.default_factories]
vector_store = "my_project.get_qdrant_vector_store"
```

The key `vector_store` is the name of the component type for which you are setting the default configuration. To see all possible component types, refer to the [List of Component Types](#list-of-component-types) section below. The `[tool.ragbits.core.default_factories]` may contain multiple keys, each corresponding to a different component type. For example:

```toml
[tool.ragbits.core.default_factories]
vector_store = "my_project.get_qdrant_vector_store"
embedder = "my_project.get_litellm_embedder"
```

<a name="llm-configuration"></a>
!!! info "LLM Specific Configuration"
    Ragbits can distinguish between LLMs, depending on their capabilities. You can use a special `[tool.ragbits.core.default_llm_factories]` section in your `pyproject.toml` file to set the default LLM factory functions for different types of LLMs. For example:

    ```toml
    [tool.ragbits.core.default_llm_factories]
    text = "my_project.get_text_llm"
    vision = "my_project.get_vision_llm"
    structured_output = "my_project.get_structured_output_llm"
    ```

    The keys in the `[tool.ragbits.core.default_llm_factories]` section are the names of the LLM types for which you are setting the default configuration. The possible LLM types are `text`, `vision`, and `structured_output`. The values are the full Python paths to the factory functions that create instances of the LLMs.

### By a YAML Configuration File
To set the default configuration for a component using a YAML configuration file, you need to create a YAML file that contains the default configuration for different types of components. You then set the path to this file in the `[tool.ragbits.core]` section of your project's `pyproject.toml` file.

For example, to designate `QdrantVectorStore` (with an in-memory `AsyncQdrantClient`) as the default vector store implementation, you can create a YAML file like this:

```yaml
vector_store:
  type: QdrantVectorStore
  config:
    client:
      location: ":memory:"
    index_name: my_index
```

Then, you set the path to this file as `default_instances_config_path` in the `[tool.ragbits.core]` section of your project's `pyproject.toml` file:

```toml
[tool.ragbits.core]
default_instances_config_path = "default_instances.yaml"
```

For subclasses built into Ragbits, you can use either the name of the class alone (like the `QdrantVectorStore` in the example above) or the full Python path to the class (like `ragbits.core.vector_stores.QdrantVectorStore`). For other classes (like your own custom implementations of Ragbits components), you must use the full Python path.

The `vector_store` key is the name of the component type for which you are setting the default configuration. To see all possible component types, refer to the [List of Component Types](#list-of-component-types). The YAML configuration may contain multiple keys, each corresponding to a different component type. For example:

```yaml
vector_store:
  type: QdrantVectorStore
  config:
    client:
      location: ":memory:"
    index_name: my_index

embedder:
  type: LiteLLMEmbeddings
  config:
    model: text-embedding-3-small
```

<a name="ds-configuration"></a>
!!! info "`DocumentSearch` Specific Configuration"
    While you can provide `DocumentSearch` with a default configuration in the same way as other components (by setting the `document_search` key in the YAML configuration file), there is also a shortcut. If you don't provide a default configuration for `DocumentSearch` explicitly, Ragbits will look for the default configuration of all the components it uses (like `vector_store`, `provider`, `rephraser`, `reranker`, etc.) and use them as its own default configuration. This way, you don't have to configure those components twice (once for `DocumentSearch` and once for the component itself).

    This is an example of a YAML configuration file that sets the default configuration for `DocumentSearch` explicitly:

    ```yaml
    document_search:
      type: DocumentSearch
      config:
        embedder:
          type: NoopEmbeddings
        vector_store:
          type: InMemoryVectorStore
    ```

    This is an example of a YAML configuration file that sets the default configuration for `DocumentSearch` implicitly:

    ```yaml
    embedder:
      type: NoopEmbeddings
    vector_store:
      type: InMemoryVectorStore
    ```

    In both cases, `DocumentSearch` will use `NoopEmbeddings` as the default embedder and `InMemoryVectorStore` as the default vector store.


## Using the Default Components
Your default configuration is used automatically by the [Ragbits CLI](../../cli/main.md). The `ragbits` commands that work on components (like [`ragbits vector-store`](../../cli/main.md#ragbits-vector-store), [`ragbits document-search`](../../cli/main.md#ragbits-document-search), etc.) will use the default component configuration unless instructed otherwise.

You can also use the default configuration in your code by instantiating the component using the `subclass_from_defaults()` factory method of [the base class of the given component type](#list-of-component-types). This method will create an instance of the default implementation of the component using the default configuration.

For example, this will create an instance of the default vector store implementation with the default configuration (as long as you have set the default vector store in the project configuration):

```python
from ragbits.core.vector_stores import VectorStore

vector_store = VectorStore.subclass_from_defaults()
```

Note that `VectorStore` itself is an abstract class, so the instance created by `subclass_from_defaults()` will be an instance of one of the concrete subclasses of `VectorStore` that you have set as the default in the project configuration.


<a name="llm-usage"></a>
!!! note "LLM Specific Usage"
    If you [set the default LLM factory functions](#llm-configuration) in the project configuration, you can use the `get_preferred_llm()` function to create an instance of the preferred LLM for a given type. For example:

    ```python
    from ragbits.core.llms.factory import get_default_llm, LLMType
    text_llm = get_default_llm(LLMType.TEXT)  # one of: TEXT, VISION, STRUCTURED_OUTPUT
    ```

### List of Component Types
This is the list of component types for which you can set default configuration:

| Key                  | Package                   | Base class                                        | Notes                                |
|----------------------|---------------------------|---------------------------------------------------|--------------------------------------|
| `embedder`           | `ragbits-core`            | [`Embeddings`][ragbits.core.embeddings.Embeddings]|                                      |
| `llm`                | `ragbits-core`            | [`LLM`][ragbits.core.llms.LLM]                    | Specifics: [Configuration](#llm-configuration), [Usage](#llm-usage)|
| `metadata_store`     | `ragbits-core`            | [`MetadataStore`][ragbits.core.metadata_stores.base.MetadataStore]||
| `vector_store`       | `ragbits-core`            | [`VectorStore`][ragbits.core.vector_stores.base.VectorStore]|          |
| `history_compressor` | `ragbits-conversations`   | [`ConversationHistoryCompressor`][ragbits.conversations.history.compressors.base.ConversationHistoryCompressor]| |
| `document_search`    | `ragbits-document-search` | [`DocumentSearch`][ragbits.document_search.DocumentSearch]| Specifics: [Configuration](#ds-configuration)|
| `provider`           | `ragbits-document-search` | [`BaseProvider`][ragbits.document_search.ingestion.providers.base.BaseProvider]||
| `rephraser`          | `ragbits-document-search` | [`QueryRephraser`][ragbits.document_search.retrieval.rephrasers.QueryRephraser]| |
| `reranker`           | `ragbits-document-search` | [`Reranker`][ragbits.document_search.retrieval.rerankers.base.Reranker]|      |

[llm-specific]: #llm-specific-behavior
[ds-specific]: #documentsearch-specific-behavior
