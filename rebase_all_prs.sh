#!/bin/bash

# Script to test rebasing all PR branches onto develop
# This will attempt each rebase and report status

DEVELOP_BRANCH="origin/develop"
BRANCHES=(
    "sc/docs-30-minutes-experience"
    "jd/feat-confirm-tool"
    "mk/morehopqa-dataset-eval"
    "jd/feat-842-oauth-discord"
    "mk/add-socrates-eval"
    "mch/outputs_feat"
    "feat/gdrive-impersonator"
    "mh/python3_13_fixes"
)

SUCCESS_BRANCHES=()
CONFLICT_BRANCHES=()

echo "========================================="
echo "Testing Rebase for All PR Branches"
echo "========================================="
echo

for branch in "${BRANCHES[@]}"; do
    echo "Testing: $branch"
    echo "-----------------------------------"

    # Checkout the branch
    git checkout "$branch" 2>&1

    # Attempt rebase
    if git rebase "$DEVELOP_BRANCH" 2>&1; then
        echo "✓ $branch - Rebased successfully"
        SUCCESS_BRANCHES+=("$branch")
    else
        echo "✗ $branch - Has conflicts"
        echo "Conflicted files:"
        git diff --name-only --diff-filter=U | sed 's/^/  - /'
        CONFLICT_BRANCHES+=("$branch")
        git rebase --abort
    fi

    echo
done

# Switch back to working branch
git checkout claude/rebase-all-prs-01UMA2VhrUMtN5t2CHR3SCxn

echo "========================================="
echo "SUMMARY"
echo "========================================="
echo
echo "Successfully rebased (${#SUCCESS_BRANCHES[@]} branches):"
for branch in "${SUCCESS_BRANCHES[@]}"; do
    echo "  ✓ $branch"
done
echo
echo "Failed with conflicts (${#CONFLICT_BRANCHES[@]} branches):"
for branch in "${CONFLICT_BRANCHES[@]}"; do
    echo "  ✗ $branch"
done
echo
echo "========================================="
echo "NEXT STEPS"
echo "========================================="
echo
if [ ${#SUCCESS_BRANCHES[@]} -gt 0 ]; then
    echo "To push successfully rebased branches:"
    for branch in "${SUCCESS_BRANCHES[@]}"; do
        echo "  git push -f origin $branch"
    done
    echo
fi

if [ ${#CONFLICT_BRANCHES[@]} -gt 0 ]; then
    echo "Branches with conflicts need manual resolution:"
    for branch in "${CONFLICT_BRANCHES[@]}"; do
        echo "  - $branch"
    done
    echo
    echo "For each conflicted branch:"
    echo "  1. git checkout <branch>"
    echo "  2. git rebase origin/develop"
    echo "  3. Resolve conflicts manually"
    echo "  4. git add <resolved-files>"
    echo "  5. git rebase --continue"
    echo "  6. Repeat steps 3-5 until rebase completes"
    echo "  7. git push -f origin <branch>"
fi
