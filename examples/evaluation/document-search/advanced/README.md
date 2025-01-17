# Document Search Evaluation

## Evaluation

### Evaluation on ingested data

```sh
uv run evaluate.py pipeline=document_search
```

```sh
uv run evaluate.py pipeline=document_search +experiments=chunking-250
```

```sh
uv run evaluate.py --multirun pipeline=document_search +experiments=chunking-250,chunking-500,chunking-1000
```

### Evaluation with new ingest

```sh
uv run evaluate.py pipeline=document_search_ingest
```

```sh
uv run evaluate.py pipeline=document_search_ingest +experiments=chunking-250
```

```sh
uv run evaluate.py --multirun pipeline=document_search_ingest +experiments=chunking-250,chunking-500,chunking-1000
```

### Logging

```sh
uv run evaluate.py logger.local=True
```

```sh
uv run evaluate.py logger.neptune=True
```

## Optimization

```sh
uv run optimize.py
```
