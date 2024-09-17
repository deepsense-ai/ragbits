#!/bin/bash

if [ ! -d .venv ]; then
    uv venv --python 3.10
    source .venv/bin/activate

    # Install all packages in editable mode
    uv sync
fi

source .venv/bin/activate
