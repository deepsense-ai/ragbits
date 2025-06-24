#!/bin/bash

set -e

set -a
source .env
set +a

PR_BRANCH="${GITHUB_HEAD_REF:-${GITHUB_REF##*/}}"


docker run -d --rm -e POSTGRES_USER=ragbits_example \
  -e POSTGRES_PASSWORD=ragbits_example \
  -e POSTGRES_DB=ragbits_example \
  -p 5432:5432 \
  pgvector/pgvector:0.8.0-pg17

docker run -d -p 6333:6333 qdrant/qdrant

find examples -name '*.py' | while read file; do
  echo "Patching dependencies for the script: $file"
  tmp_file=$(mktemp)
  cp "$file" "$tmp_file"
  python patch_dependencies.py "$tmp_file" "$PR_BRANCH"

  echo "Running the script..."
  uv run "$tmp_file"
done

echo "All examples validated successfully."
