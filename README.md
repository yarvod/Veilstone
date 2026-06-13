# Veilstone

Veilstone is an original Python voxel sandbox engine prototype. It uses Python 3.13,
`uv`, pyglet, ModernGL, and NumPy. The project is being built in small, tested phases.

## Development setup

```bash
uv sync
uv run python -m voxel_sandbox
```

This is the player-facing entry point. It opens the Main Menu with Singleplayer,
Multiplayer, Settings, and Exit. The technical commands remain available for development
and dedicated server use:

```bash
uv run python -m voxel_sandbox --help
uv run python -m voxel_sandbox client
uv run python -m voxel_sandbox server
uv run python -m voxel_sandbox host
```

Quality checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

The committed `.python-version` and `pyproject.toml` keep the project on Python 3.13.
Runtime settings live in `config/settings.toml`.

Client controls:

- Arrow keys or `W/S` and `Enter`: navigate menus.
- `W/A/S/D`: move horizontally.
- `Space` / `Shift`: move up / down in the free camera.
- Mouse: look around.
- `Escape`: open the Pause Menu while playing, or go back in menus.
- `F5`: force shader reload.

## Architecture

- `app`: composition root, settings, and executable modes.
- `domain`: gameplay definitions and rules without rendering dependencies.
- `engine`: data-oriented world, physics, generation, and simulation.
- `render`: window, camera, shaders, meshes, and GPU resources.
- `infrastructure`: logging, storage, assets, and profiling adapters.
- `tests`: unit, integration, and performance coverage.

Architecture decisions are recorded in `docs/adr`.
