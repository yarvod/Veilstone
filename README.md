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
uv run python -m voxel_sandbox client --connect 127.0.0.1:25565
uv run python -m voxel_sandbox server
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-worldgen
uv run python -m voxel_sandbox benchmark-physics
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-streaming
uv run python -m voxel_sandbox benchmark-frame-streaming
uv run python -m voxel_sandbox benchmark-network
```

Singleplayer uses the same server-authoritative simulation planned for multiplayer:
the game client owns an in-process local server. `Open to LAN` exposes that server to
other clients instead of launching a separate player-facing mode. The standalone
`server` command is for dedicated LAN hosting and development.

Quality checks:

```bash
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m smoke
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Pytest markers separate isolated unit tests from subsystem integration and real application
smoke tests. Hypothesis covers broad coordinate invariants and automatically shrinks failing
examples. The smoke suite creates the actual OpenGL context, compiles shaders, renders the
menu and world once, and starts the dedicated server entry point.

The committed `.python-version` and `pyproject.toml` keep the project on Python 3.13.
Runtime settings live in `config/settings.toml`.
World generation and section meshing use reusable process pools by default. CPU work stays
off the render thread, while `mesh_uploads_per_frame` amortizes OpenGL uploads.

Client controls:

- Arrow keys or `W/S` and `Enter`: navigate menus.
- `W/A/S/D`: walk; physical key positions remain usable with a non-English macOS layout.
- `Space`: jump.
- Mouse: look around.
- Left mouse: break the highlighted block.
- `1` / `2`: select grass or a Gloam Lantern for placement.
- Right mouse: place the selected block on the highlighted face.
- `Escape`: open the Pause Menu while playing, or go back in menus.
- `F5`: force shader reload.
- `F6`: toggle smooth lighting.
- `F7`: toggle ambient occlusion.
- `F8`: toggle fog.
- `F9`: toggle greedy/visible-face meshing for visual comparison.

## Architecture

- `app`: composition root, settings, and executable modes.
- `domain`: gameplay definitions and rules without rendering dependencies.
- `engine`: data-oriented world, physics, generation, and simulation.
- `render`: window, camera, shaders, meshes, and GPU resources.
- `infrastructure`: logging, storage, assets, and profiling adapters.
- `tests`: unit, integration, and performance coverage.

Architecture decisions are recorded in `docs/adr`.

Current prototype state: selecting Create World or Load World enters a rendered generated
world with original programmatic block textures. Chunks stream around the player on
background workers while the overlay reports loaded, pending, visible, lighting, and mesh
counts.

## Test Phase 5

```bash
uv run python -m voxel_sandbox
```

1. Select `Singleplayer`, then `Create World`.
2. Fly with `W/A/S/D`, `Space`, and `Shift`; use the mouse to look around.
3. Watch `Chunks` and `Pending` in the overlay while crossing chunk boundaries.
4. Confirm terrain includes caves, dusk crystal ore, and veilwood trees.
5. Press `Escape` to verify the Pause Menu, then choose `Resume`.

The prototype render distance, seed, generation worker count, and upload budget can be
changed under `[world]` in `config/settings.toml`.

## Test Phase 6

```bash
uv run python -m voxel_sandbox
```

1. Select `Singleplayer -> Create World` and wait for the player to land.
2. Walk with `W/A/S/D`; confirm terrain and trees block movement.
3. Jump with `Space`; confirm jumping is unavailable while airborne.
4. Aim with the crosshair and confirm the target block receives a gold outline.
5. Break blocks with left mouse and place grass blocks with right mouse.
6. Walk away until chunks unload, then return and confirm edits remain for the session.

Player physics benchmark:

```bash
uv run python -m voxel_sandbox benchmark-physics
```

## Test Phase 7

```bash
uv run python -m voxel_sandbox
```

1. Select `Singleplayer -> Create World` and compare open terrain, shaded sides, and corners.
2. Press `F6` and `F7`; confirm smooth lighting and ambient occlusion visibly toggle.
3. Press `2`, then place a Gloam Lantern with right mouse in a dark recess or small cave.
4. Break the lantern with left mouse; confirm its warm block light disappears.
5. Walk away from terrain and press `F8`; confirm distance fog toggles.
6. Observe the sky and terrain tint change during the configured day/night cycle.

Lighting benchmark:

```bash
uv run python -m voxel_sandbox benchmark-lighting
```

The cycle duration and graphics defaults can be changed under `[graphics]` in
`config/settings.toml`. Set `day_cycle_seconds = 30.0` for a faster manual check.

## Test Phase 8

```bash
uv run python -m voxel_sandbox
```

1. Enter `Singleplayer -> Create World` and inspect flat terrain, slopes, trees, and caves.
2. Press `F9` to switch between `greedy` and `visible` in the debug overlay.
3. Confirm textures keep their block-sized scale and lighting does not gain border seams.
4. Compare `Triangles` in both modes; greedy mode should be substantially lower.
5. Toggle `F6`/`F7` in both mesh modes and confirm smooth light/AO remain coherent.

```bash
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-lighting
```

Block and sky light use bounded voxel propagation, not per-light ray tracing. Sun cast
shadows are planned as a GPU shadow-map pass in Phase 15; see
`docs/adr/0002-voxel-lighting-and-shadows.md`.
