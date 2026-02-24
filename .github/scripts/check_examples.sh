#!/bin/bash

# Check that all example Python files:
#   1. Are documented in examples/README.md
#   2. Have the "# /// script" uv inline script metadata tag

EXAMPLES_DIR="examples"
README="examples/README.md"

MISSING_README=()

while IFS= read -r -d '' file; do
    rel_path="${file#./}"
    readme_path="/${rel_path}"

    if ! grep -qF "$readme_path" "$README"; then
        MISSING_README+=("$readme_path")
    fi
done < <(find "$EXAMPLES_DIR" -name "*.py" -print0 | sort -z)

FAILED=0

if [ ${#MISSING_README[@]} -gt 0 ]; then
    echo "ERROR: The following example files are not documented in $README:"
    for f in "${MISSING_README[@]}"; do
        echo "  - $f"
    done
    echo ""
    echo "Please add entries for these files to the table in $README."
    FAILED=1
fi

if [ $FAILED -eq 1 ]; then
    exit 1
fi

echo "All example files are documented in $README."
