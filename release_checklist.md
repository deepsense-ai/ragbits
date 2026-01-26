# Release Checklist

## Known Issues

### DeepEval Unused Dependencies

**Issue:** DeepEval installs unused dependencies that are not required for our use case:
- `google-genai`
- `ollama`
- `pytest-xdist`

**Status:** Currently, there is no way to install DeepEval without these dependencies.

**Resolution:** These dependencies have been temporarily whitelisted in `.libraries-whitelist.txt`.

### Dependency Version Pins in CI

**Issue:** Test failures occur when ragbits is installed from built packages (wheel files) rather than using `uv.lock`. Different versions of the following libraries are resolved by the package manager during installation from builds, causing compatibility issues with the test suite:
- `pyarrow`
- `ray`
- `docling`
- `torch`

**Status:** These are temporary workarounds until the underlying dependency conflicts are properly resolved.

**Resolution:** Pinned specific versions in `.github/workflows/shared-packages.yml`:
- `pyarrow==17.0.0`
- `ray==2.43.0`
- `docling==2.15.1`
- `torch==2.2.2`