# Installation

## Build from source

Dependencies needed to build and run Ragbits from the source code:

1. [**uv**](https://docs.astral.sh/uv/getting-started/installation/)
2. [**python**](https://docs.astral.sh/uv/guides/install-python/) 3.10


## Linting and formatting
We use `ruff` for linting and formatting our code. To format your code, run:

```bash
$ uv run ruff format
```

To lint the code, run:
```bash
$ uv run ruff check --fix
```

## Type checking
We use `mypy` for type checking. To perform type checking, simply run:

```bash
$ uv run mypy .
```

## Testing
We use `pytest` for testing. To run the tests, simply run:

```bash
$ uv run pytest
```

Running integration tests requires:
- PostgreSQL with the pgvector extension installed (minimum pgvector version: 0.7.0, which added sparse vector support),
- Weaviate available on `localhost:8080`.

### Docker

The easiest way to run both dependencies locally is Docker Compose. Start both PostgreSQL (pgvector) and Weaviate with:

```bash
docker compose up -d
```

You can check that services are healthy with:

```bash
docker compose ps
```

And stop them with:

```bash
docker compose down
```

### Ubuntu

On Ubuntu Linux you can get in by installing the `postgresql-17-pgvector` package.

If it is not in your system's default repositories, you can install it from the official PostgreSQL Apt Repository:

```bash
sudo apt install postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install postgresql-17-pgvector
```

You still need a running Weaviate instance (for example via Docker Compose):

```bash
docker compose up -d weaviate
```

## Install pre-commit or pre-push hooks

We also recommend to run checkers on pre-commit/push hook. To set it up, follow these steps:

```bash
$ uv run scripts/install_git_hooks.py
```

Then decide whether you want to run the checks before each commit or before each push.
