#!/bin/bash
# Script to remove Claude Code signatures from commit messages on the current branch
# Usage: ./scripts/remove-claude-signature.sh [base_branch]
#   base_branch: The branch to compare against (default: main)

set -e

BASE_BRANCH="${1:-main}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Removing Claude signatures from commits on '$CURRENT_BRANCH' since '$BASE_BRANCH'"

# Get the merge base
MERGE_BASE=$(git merge-base "$BASE_BRANCH" HEAD)

# Count commits to be processed
COMMIT_COUNT=$(git rev-list --count "$MERGE_BASE..HEAD")
echo "Found $COMMIT_COUNT commits to process"

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo "No commits to process"
    exit 0
fi

# Use git filter-branch to rewrite commit messages
git filter-branch -f --msg-filter '
sed -e "/^🤖 Generated with \[Claude Code\]/d" \
    -e "/^Co-Authored-By: Claude/d" \
    -e "/^Co-authored-by: Claude/d" | \
sed -e :a -e "/^[[:space:]]*$/{\$d;N;ba;}"
' "$MERGE_BASE..HEAD"

echo "Done! Claude signatures have been removed from commit messages."
echo ""
echo "To verify, run: git log --oneline $BASE_BRANCH..HEAD"
echo ""
echo "WARNING: This rewrote history. If you had already pushed these commits,"
echo "you will need to force push: git push --force-with-lease"
