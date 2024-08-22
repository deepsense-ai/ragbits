#!/bin/bash

if [ ! -d venv ]; then
    python3 -m venv venv
    . venv/bin/activate
    pip install --upgrade pip
    pip install --quiet wheel==0.41.3
    pip install --quiet -r requirements-dev.txt

    # Install all packages in editable mode
    for dir in packages/*/; do pip install -e "$dir"; done

fi

. venv/bin/activate
