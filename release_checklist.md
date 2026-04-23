# Release Checklist

## Known Issues

**Issue:** `RayDistributedIngestStrategy` hangs in CI when ragbits is installed in package mode (via `uv pip install`). Ray 2.47+ enables a uv runtime env hook by default, which causes worker processes to fail when the environment is not managed by `uv sync`

**Status:** Resolved

**Resolution:** Set `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0` in `.github/workflows/shared-packages.yml` to disable the uv runtime env hook for Ray workers. This is the [officially recommended approach](https://github.com/ray-project/ray/releases/tag/ray-2.47.0) for environments where dependencies are installed outside of `uv sync`
