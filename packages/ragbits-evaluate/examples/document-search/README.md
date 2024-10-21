# Document Search Evaluation

## Ingest

```sh
uv run ingest.py
```

```sh
uv run ingest.py +experiments=chunking-250
```

```sh
uv run ingest.py --multirun +experiments=chunking-250,chunking-500,chunking-1000
```

## Evaluate

```sh
uv run evaluate.py
```

```sh
uv run evaluate.py +experiments=chunking-250
```

```sh
uv run evaluate.py --multirun +experiments=chunking-250,chunking-500,chunking-1000
```
