#!/bin/bash

set -euo pipefail

# Find all Python files with script sections and output as JSON array
examples=()

while IFS= read -r -d '' file; do
    if grep -q "^# /// script" "$file"; then
        examples+=("$file")
    fi
done < <(find examples -name '*.py' -type f -print0)

# Convert to JSON format for GitHub Actions matrix
printf '{"example":['
for i in "${!examples[@]}"; do
    if [ $i -gt 0 ]; then
        printf ','
    fi
    printf '"%s"' "${examples[$i]}"
done
printf ']}'
