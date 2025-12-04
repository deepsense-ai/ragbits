# Release Checklist

## Known Issues

### DeepEval Unused Dependencies

**Issue:** DeepEval installs unused dependencies that are not required for our use case:
- `google-genai`
- `ollama`
- `pytest-xdist`

**Status:** Currently, there is no way to install DeepEval without these dependencies.

**Resolution:** These dependencies have been temporarily whitelisted in `.libraries-whitelist.txt`.