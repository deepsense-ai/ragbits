# How to Ingest Documents in a distributed fashion

Ragbits Document Search can ingest documents in a distributed fashion if it's installed with `distributed` extra. This can be set up by specifying the `DistributedProcessing` execution strategy when creating the `DocumentSearch` instance.

```python
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.ingestion.processor_strategies.distributed import DistributedProcessing

documents = [
    DocumentMeta.create_text_document_from_literal("Example document 1"),
    DocumentMeta.create_text_document_from_literal("Example document 2"),
]

embedder = LiteLLMEmbeddings(
    model="text-embedding-3-small",
)

vector_store = InMemoryVectorStore()

processing_strategy = DistributedProcessing()

document_search = DocumentSearch(
    embedder=embedder,
    vector_store=vector_store,
    processing_strategy=processing_strategy
)
```

## Local document ingestion

By default, when run outside of a Ray cluster, the Ray Core library will parallelize the processing of documents on the local machine, using cores available on the machine. If that is acceptable, you can just use the code above and the documents will be processed in parallel on the local machine.

## Remote document ingestion

When run inside a Ray cluster, the Ray Core library will parallelize the processing of documents across the nodes in the cluster. There are several ways of sending documents to the Ray cluster for processing, but using Ray Jobs API is by far the most recommended one.  
To use Ray Jobs API, you should prepare the processing script and the documents to be processed, and then submit the job to the Ray cluster.
Make sure to replace `<cluster_address>` with the address of your Ray cluster and adjust the `entrypoint` and `runtime_env` parameters to match your setup.

```python
from ray.job_submission import JobSubmissionClient

client = JobSubmissionClient("http://<cluster_address>:8265")
job_id = client.submit_job(
    entrypoint="python script.py",
    runtime_env={
        "working_dir": "./", 
        "pip": [
            "ragbits-core[litellm]",
            "ragbits-document-search[distributed]"
        ]
    },
)
print(job_id)
```

Ray Jobs is also available as CLI commands. You can submit a job using the following command:

```bash
ray job submit \
    --address http://<cluster_address>:8265 \
    --runtime-env '{"pip": ["ragbits-core[litellm]", "ragbits-document-search[distributed]"]}'\
    --working-dir . \
    -- python script.py
```

There are also other ways to submit jobs to the Ray cluster. For more information, please refer to the [Ray documentation](https://docs.ray.io/en/latest/ray-overview/index.html).