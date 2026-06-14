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

GitHub's hosted Windows runner exposes an OpenGL implementation below the game's 3.3 minimum.
CI therefore verifies the Windows executable, bundled resources, user-data writes, and dedicated
server there. A graphical `Veilstone --smoke-test` on a Windows machine with OpenGL 3.3 or newer
is still required before publishing a release.
