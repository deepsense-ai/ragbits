# Document Search Evaluation

## Evaluation

### Evaluation on ingested data

```sh
uv run evaluate.py
```

```sh
uv run evaluate.py +experiments=chunking-250
```

```sh
uv run evaluate.py --multirun +experiments=chunking-250,chunking-500,chunking-1000
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

### Monitoring

```sh
uv run optimize.py neptune_callback=True
```
