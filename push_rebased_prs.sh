#!/bin/bash

# Script to push successfully rebased PR branches
# Run this script to push all the branches that were successfully rebased

echo "========================================="
echo "Pushing Rebased PR Branches"
echo "========================================="
echo

# Array of successfully rebased branches
BRANCHES=(
    "sc/docs-30-minutes-experience"
    "mch/outputs_feat"
    "mh/python3_13_fixes"
)

# Function to push with retries
push_with_retry() {
    local branch=$1
    local max_attempts=5
    local attempt=1
    local wait_time=2

    while [ $attempt -le $max_attempts ]; do
        echo "Pushing $branch (attempt $attempt/$max_attempts)..."

        if git push -f origin "$branch"; then
            echo "✓ Successfully pushed $branch"
            return 0
        else
            if [ $attempt -lt $max_attempts ]; then
                echo "⚠ Push failed, waiting ${wait_time}s before retry..."
                sleep $wait_time
                wait_time=$((wait_time * 2))  # Exponential backoff
                attempt=$((attempt + 1))
            else
                echo "✗ Failed to push $branch after $max_attempts attempts"
                return 1
            fi
        fi
    done
}

# Push each branch
FAILED_PUSHES=()
for branch in "${BRANCHES[@]}"; do
    echo "-----------------------------------"
    git checkout "$branch"

    if ! push_with_retry "$branch"; then
        FAILED_PUSHES+=("$branch")
    fi

    echo
done

# Return to working branch
git checkout claude/rebase-all-prs-01UMA2VhrUMtN5t2CHR3SCxn

echo "========================================="
echo "PUSH SUMMARY"
echo "========================================="
echo

if [ ${#FAILED_PUSHES[@]} -eq 0 ]; then
    echo "✓ All branches pushed successfully!"
else
    echo "Failed to push ${#FAILED_PUSHES[@]} branch(es):"
    for branch in "${FAILED_PUSHES[@]}"; do
        echo "  ✗ $branch"
    done
    echo
    echo "Please try pushing these manually or check network connectivity."
fi
