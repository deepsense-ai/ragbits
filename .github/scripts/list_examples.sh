#!/bin/bash

set -euo pipefail

# Find all Python files with script sections and output as JSON array
examples=()

while IFS= read -r -d '' file; do
    if grep -q "^# /// script" "$file"; then
        examples+=("$file")
    fi
done < <(find examples -name '*.py' -type f -print0)

# Convert to JSON format for GitHub Actions matrix with skip information
printf '{"include":['
for i in "${!examples[@]}"; do
    if [ $i -gt 0 ]; then
        printf ','
    fi

    # Check if this example should be skipped
    should_skip="false"
    if [ -f ".github/scripts/example_cache.sh" ]; then
        should_skip=$(bash .github/scripts/example_cache.sh check "${examples[$i]}" || echo "false")
    fi

    printf '{"example":"%s","skip":%s}' "${examples[$i]}" "$should_skip"
done
printf ']}'
