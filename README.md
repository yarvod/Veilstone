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
uv run python -m voxel_sandbox benchmark-server
uv run python -m voxel_sandbox benchmark-shadows
uv run python -m voxel_sandbox structure-preview veilstone_ruin
```

Singleplayer uses the same server-authoritative transport as multiplayer:
the game client owns and connects to an in-process local server. `Open to LAN` exposes
that server to other clients instead of launching a separate player-facing mode. The
standalone `server` command is for dedicated LAN hosting and development.

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
`graphics.shadow_quality` accepts `off`, `low`, or `medium`; `graphics.shadow_bias`
controls terrain shadow acne correction.
`graphics.clouds` toggles procedural clouds and `graphics.postprocess` enables the optional
tone-mapping/vignette framebuffer pass.
Player overrides are written atomically to `saves/settings.toml`. The Settings screen exposes
graphics toggles, VSync, and `peaceful`/`normal` difficulty; Controls supports conflict-checked
movement/jump rebinding. Peaceful removes hostile mobs. Normal allows one nearby hostile mob only
where effective skylight/block light is level 7 or lower.
The Audio screen persists master, effects, music, and ambience volume groups. Positional block
sounds, material footsteps, distinct cow/zombie feedback, biome ambience, and state-driven music
use per-resource gain staging through a backend-independent event bus; dedicated servers use a
silent backend.
Cow and zombie mobs use original generated material sheets and versioned articulated model
definitions. Per-part UV regions, joint pivots, inherited transforms, gravity, buoyancy, and
distance LOD keep their silhouettes and movement readable without copying third-party assets.
World generation and section meshing use reusable process pools by default. CPU work stays
off the render thread, while `mesh_uploads_per_frame` amortizes OpenGL uploads.
Versioned TOML structure templates generate deterministic ruins, camps, and rare dusk spires;
the developer preview command prints their validated block layers and loot tables.
Singleplayer state is autosaved under `saves/dev_world`: versioned world metadata, compressed
chunk files, active runtime structures, and the local player's position, health, hotbar, and
inventory. Runtime gates, altars, and bridges animate through render transforms instead of chunk
remeshing; their collision and state are server-authoritative and replicated over LAN.

## Packaging

Build the native application on the target operating system:

```bash
uv sync --frozen
uv run python scripts/build_app.py
```

On macOS this produces `dist/Veilstone.app`; Windows and Linux produce a `dist/Veilstone`
directory. Packaged builds store settings, saves, and crash logs in the platform user-data
directory. `VEILSTONE_DATA_DIR` overrides that location for automated tests. See
`docs/RELEASE.md` for the complete release gate.

Local multiplayer developer run:

```bash
uv run python -m voxel_sandbox server --port 25565
uv run python -m voxel_sandbox client --connect 127.0.0.1:25565
```

The remote client receives server chunks, player snapshots, block deltas, and chat protocol
messages. LAN discovery, Direct Connect, nickname editing, chat, reconnect, and Open to LAN
are available through the game UI.

Client controls:

- Arrow keys or `W/S` and `Enter`: navigate menus.
- `W/A/S/D`: walk; physical key positions remain usable with a non-English macOS layout.
- `Space`: jump.
- Mouse: look around.
- Left mouse: break the highlighted block.
- Left mouse while aiming at a mob: damage the mob; death produces an item entity.
- `1-9` or mouse wheel: select a hotbar slot.
- `E`: open the 9x4 inventory and player 2x2 crafting grid.
- Left click / right click in inventory: transfer or split stacks.
- `Shift` + left click in inventory: quick-move between hotbar and backpack.
- Click the crafting output, or press `C`, to take one matching recipe result.
- `Q`: drop one item from the selected hotbar stack.
- `T`: enter and send a multiplayer chat message.
- `/`: open the command line. Use `/help`, `/time set day|noon|night|midnight|<ticks>`, or
  `/difficulty peaceful|normal`. Developer structure commands are `/structure spawn
  gate|altar|bridge`, `/structure toggle ID`, and `/structure list`.
- Right mouse: toggle an aimed runtime structure, otherwise place the selected block on the
  highlighted face.
- `Escape`: open the Pause Menu while playing, or go back in menus.
- Pause Menu -> `Open to LAN`: advertise the running singleplayer server on the LAN.
- `F3`: toggle the detailed debug overlay.
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
world with its own seed, metadata, and player save. Chunks stream around the player on
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

## Test Phase 9

```bash
uv run python -m voxel_sandbox
```

1. Select `Singleplayer -> Create World` and locate a generated lake below elevation 32.
2. Inspect the animated transparent surface and shore geometry from above and below water.
3. Press `3`, then place water over a ledge and verify downward then sideways flow.
4. Enter water and verify the view changes to short-range blue underwater fog.
5. Cross chunk boundaries near water and watch the frame-time overlay for streaming spikes.

## Test Phase 10

```bash
uv run python -m voxel_sandbox
```

1. Switch hotbar slots with `1-9` or the mouse wheel and place a selected block.
2. Break Veilwood logs and approach their positions until the `Drops` counter decreases.
3. Press `E` and test stack transfer, splitting, and Shift-click quick move.
4. Press `C` to turn a log into four planks, then craft a Runecraft Table from four planks.
5. Place and right-click the Runecraft Table to activate 3x3 recipes.
6. Press `Q` to drop one selected item and collect it again by walking nearby.

## Test Phase 11

```bash
uv run python -m voxel_sandbox
```

1. Observe blue-gray passive mobs wandering and crimson hostile mobs chasing nearby players.
2. Let a hostile reach melee range and verify the debug `Health` value decreases.
3. Aim at either mob and left-click until it dies and creates a small gold item entity.
4. Walk over the drop to collect it, or press `Q` to create another visible item entity.
5. Move far enough to trigger despawn and verify the local population replenishes near the player.

## Test Phase 12

```bash
uv run python -m voxel_sandbox
```

1. Edit terrain, change inventory and selected hotbar slot, move, then exit normally.
2. Restart and choose `Singleplayer -> Load World`; verify world and player state are restored.
3. Cross chunk boundaries after an edit and return to verify unload/reload persistence.
4. Inspect `saves/dev_world/level.toml`, `players/local_player.json`, and `regions/*.vchk`.

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

Block and sky light use bounded voxel propagation, not per-light ray tracing. Sun-cast
shadows use a GPU shadow map with configurable quality, bias, and PCF; see
`docs/adr/0002-voxel-lighting-and-shadows.md`.
