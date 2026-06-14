# Release checklist

1. Run `uv sync --frozen`.
2. Run `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pyright`.
3. Run `uv run pytest -q` and all performance benchmarks.
4. Run `uv build` and inspect wheel resources.
5. Run `uv run python scripts/build_app.py` on each target operating system.
6. Smoke-test `Veilstone --smoke-test` from the packaged output.
7. Confirm saves, settings, and crash logs use the platform user-data directory.
8. Tag the release and attach platform artifacts with checksums.

Windows packaging must run on Windows; macOS packaging must run on macOS. PyInstaller does not
cross-compile native application bundles.
