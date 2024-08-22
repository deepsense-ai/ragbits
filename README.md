# RAG-Stack (to be renamed)

Repository for internal experiment with our upcoming LLM framework.


# Setup developer environment

To start, you need to setup your local machine.

## Setup venv

You need to setup virtual environment, simplest way is to run from project root directory:

```bash
$ . ./setup_dev_env.sh
$ source venv/bin/activate
```
This will create a new venv and install all packages from this repository in editable mode.
It will also intall their dependencies and the dev dependencies from `requirements-dev.txt`.
