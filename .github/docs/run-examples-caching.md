# GitHub Actions Scripts

## Example Caching System

This directory contains scripts that implement a smart caching mechanism for running examples in CI:

### How it works

1. **`list_examples.sh`** - Discovers all runnable Python examples and generates a matrix that includes skip information
2. **`example_cache.sh`** - Consolidated script with subcommands:
   - `check <example_file>` - Checks if an example should be skipped based on previous successful run and file modifications
   - `record <example_file>` - Records successful example runs with the current commit hash
3. **`run_single_example.sh`** - Runs individual examples and records success when they complete

### Cache behavior

- Examples that passed on the current branch and haven't been modified since will be skipped
- Cache is stored per branch using GitHub Actions cache
- Cache keys include the branch name and commit hash
- Fallback to main branch cache if current branch cache doesn't exist

### Benefits

- Dramatically reduces CI time when most examples are already passing
- Only runs examples that are new, modified, or previously failed
- Maintains full test coverage while optimizing for common scenarios

### Cache storage

Cache files are stored in `.example-cache/` with the format:
- `{branch-name}-{example-path-normalized}.success` - Contains the commit hash of the last successful run
