#!/bin/bash
set -e

uv run pip-licenses --from=mixed  --ignore-packages `cat .libraries-whitelist.txt`> licenses.txt
cat licenses.txt

FOUND=$(tail -n +2 licenses.txt | grep -v -f .license-whitelist.txt | wc -l)

if [[ $FOUND -gt 0 ]]; then
  echo "Detected license/s not on the whitelist ($FOUND found)."
  tail -n +2 licenses.txt | grep -v -f .license-whitelist.txt
  exit 1
else
  echo "Okay."
  exit 0
fi
