# Document Search Evaluation

## Evaluation

### Evaluation on ingested data

```sh
uv run examples/evaluate/document-search/advanced/evaluate.py
```

```sh
uv run examples/evaluate/document-search/advanced/evaluate.py +experiments=chunking-250
```

```sh
uv run examples/evaluate/document-search/advanced/evaluate.py --multirun +experiments=chunking-250,chunking-500,chunking-1000
```

### Logging

```sh
uv run examples/evaluate/document-search/advanced/evaluate.py logger.local=True
```

```sh
uv run examples/evaluate/document-search/advanced/evaluate.py logger.neptune=True
```

## Optimization

```sh
uv run examples/evaluate/document-search/advanced/optimize.py
```

### Monitoring

```sh
uv run examples/evaluate/document-search/advanced/optimize.py neptune_callback=True
```
