# Veilstone

Veilstone is an original Python voxel sandbox engine prototype built with Python
3.13, `uv`, Pyglet, ModernGL, and NumPy.

The project is deliberately developed in small, tested phases. It already has a
playable voxel loop, world streaming, basic survival-sandbox interactions,
resource-pack experiments, audio, mobs, water, saves, and LAN multiplayer
plumbing, but it is still a prototype rather than a Minecraft-complete game.

Current planning lives in:

- `docs/WORKPLAN.md` — active roadmap and next phase.
- `docs/BUGS.md` — known bugs, rough edges, and quality-gate status.
- `docs/CHANGELOG.md` — completed meaningful changes.
- `docs/ARCHITECTURE.md` — target dependency direction and feature boundaries.

## Run

```bash
uv sync
uv run python -m voxel_sandbox
```

The normal entry point opens the main menu with Singleplayer, Multiplayer,
Settings, and Exit.

Developer entry points:

```bash
uv run python -m voxel_sandbox --help
uv run python -m voxel_sandbox server --port 25565
uv run python -m voxel_sandbox client --connect 127.0.0.1:25565
uv run python -m voxel_sandbox benchmark-worldgen
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-physics
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-streaming
uv run python -m voxel_sandbox benchmark-frame-streaming
uv run python -m voxel_sandbox benchmark-network
uv run python -m voxel_sandbox benchmark-server
uv run python -m voxel_sandbox benchmark-shadows
uv run python -m voxel_sandbox structure-preview veilstone_ruin
```

## What works today

- Main menu, singleplayer world creation/loading, pause menu, settings screens,
  and basic controls rebinding.
- Server-authoritative local singleplayer transport plus LAN discovery/direct
  connect/chat/Open LAN flows.
- Chunked voxel terrain with caves, biomes, trees, Twilight-inspired
  decorators, lighting, fog, clouds, shadows, greedy meshing, and background
  generation/meshing workers.
- Block targeting, breaking, placing, drops, item pickup/drop, hotbar, backpack,
  and simple crafting.
- Data-driven block/item/biome registries and a Minecraft Java-style resource
  pack MVP for block textures.
- Basic water blocks: passable/swimmable water, cross-chunk flow, simple source
  creation, underwater fog, and water rendering.
- Passive/hostile mobs with simple steering, gravity, buoyancy, sounds, damage,
  death drops, and generated articulated model definitions.
- Player-feel pass: coyote time, jump buffering, variable jump height, sprint,
  and subtle head bob.
- Experimental 3D local/third-person player model path behind
  `development.render_local_player_model`.
- Positional audio for UI, blocks, footsteps, mobs, ambience, and music through
  a backend-independent event bus.
- Save/load for world edits and player state.

## Known prototype gaps

These are expected rough edges, not hidden production promises:

- First-person presentation is still primitive: no proper 3D hand/viewmodel,
  held item model, swing/place/break animations, player shadow, or unified gait
  phase syncing camera bob, footsteps, and body/hand animation.
- Mob walking animation is visually rough and not yet synchronized to actual
  locomotion speed, ground contact, or step sounds.
- Water still behaves like voxel fluid. There are known movement and visual
  issues around climbing out of water, interrupted flow surfaces, and the lack
  of smooth continuous waves/splashes.
- Transparent textures are incomplete. Leaf cutouts from packs such as Faithful
  need alpha-tested/ordered rendering so the world is visible through holes.
- Inventory UI is functional but not Minecraft-polished: no 3D item icons,
  stack-count overlay in the corner of item icons, hover tooltip polish,
  drag-and-drop slot movement, or full crafting UX.
- World generation needs more distant landscape appeal, biome filling, grass,
  flowers, landmarks, and configurable in-game render distance.
- Debug/perspective controls are partial. `F3` exists for a debug overlay, but
  CPU/GPU/memory/device diagnostics and Minecraft-like perspective cycling are
  not complete.

For the live prioritized list, see `docs/WORKPLAN.md` and `docs/BUGS.md`.

## Controls

- Arrow keys / `W` / `S` / `Enter`: navigate menus.
- `W/A/S/D`: move.
- `Space`: jump.
- `Shift`: sprint.
- Mouse: look around.
- Left mouse: break highlighted block, or damage an aimed mob.
- Right mouse: place selected block on highlighted face; when aiming a runtime
  structure, toggle that structure.
- `1-9` or mouse wheel: select hotbar slot.
- `E`: open inventory and crafting UI.
- Left/right click in inventory: transfer or split stacks.
- `Shift` + left click in inventory: quick-move between hotbar and backpack.
- `C`: take one matching recipe result from the player crafting grid.
- `Q`: drop one item from the selected hotbar stack.
- `T`: open multiplayer chat.
- `/`: open command line.
- `Escape`: pause/resume or go back in menus.
- `F1`: hide/show HUD.
- `F2`: save screenshot.
- `F3`: toggle debug overlay.
- `F5`: cycle camera perspective.
- `Ctrl+F5`: reload shaders.
- `F6`: toggle smooth lighting.
- `F7`: toggle ambient occlusion.
- `F8`: toggle fog.
- `F9`: toggle greedy/visible-face meshing comparison.

Useful commands:

```text
/help
/time set day|sunrise|noon|sunset|twilight|night|midnight|<ticks>
/difficulty peaceful|normal
/resourcepack <path|default>
/structure spawn gate|altar|bridge
/structure toggle <id>
/structure list
```

`/time set day` and `/time set sunrise` set the world to the beginning of the
day. `noon` is the high-sun value.

## Settings

Runtime defaults live in `config/settings.toml`; user overrides are stored under
`saves/settings.toml`.

Important settings:

- `[world].render_distance` controls chunk radius in the config file. In-game
  render-distance UI is planned but not complete.
- `[world].generation_workers`, `[world].meshing_workers`, and upload budgets
  tune background streaming work.
- `[graphics].day_cycle_seconds = 1200.0` gives a Minecraft-like 20-minute full
  day/night cycle.
- `[graphics].shadow_quality`, `shadow_bias`, `clouds`, `postprocess`,
  `smooth_lighting`, `ambient_occlusion`, and `fog` control renderer features.
- `[audio]` controls master/effects/music/ambience volume groups; per-resource
  gains live in `config/audio.toml`.

## Resource packs

The resource-pack MVP accepts Minecraft Java-style block texture locations for a
subset of content and can load folders or ZIP packs.

Example:

```text
/resourcepack resource_packs/Faithful-32x-1.21.11
/resourcepack default
```

This is not a complete Minecraft resource-pack implementation yet. Alpha-tested
leaves, 3D item models, UI item icons, and broader asset mapping are still on
the roadmap.

## Architecture

The intended dependency direction is:

```text
domain <- engine/simulation <- application <- presentation, infrastructure, audio, network adapters
```

The practical rule for new features is: keep pure gameplay/data rules out of
Pyglet and ModernGL, add use cases/ports when a feature crosses settings,
storage, render, audio, network, or UI, and let the renderer consume snapshots
rather than own gameplay state.

Current package map:

- `voxel_sandbox.domain`: pure block, item, inventory, biome, crafting, and
  progression data/rules.
- `voxel_sandbox.engine`: chunks, physics, fluids, generation, lighting,
  events, ECS, authority, and simulation-ish systems.
- `voxel_sandbox.application`: use cases, ports, and render-facing snapshots.
- `voxel_sandbox.infrastructure`: storage and logging implementations.
- `voxel_sandbox.audio`: audio bus, registry, backend, director, and event
  mapping.
- `voxel_sandbox.network`: LAN server/client/session messages and discovery.
- `voxel_sandbox.render`: Pyglet window, ModernGL renderers, UI, controllers,
  camera, shaders, texture-pack adapters.
- `voxel_sandbox.app`: composition, settings, executable modes, and commands.

See `docs/ARCHITECTURE.md` before adding systems that touch `GameWindow`,
`DemoWorldRenderer`, controllers, storage, audio, or networking.

## Quality checks

Use focused tests while developing, then run the relevant gate before committing:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pyright
```

`pyright` is currently expected to fail only for the documented project-wide
baseline in `docs/BUGS.md` (`BUG-Q001`). Do not mix unrelated typing cleanup into
feature work unless it blocks the change.

Broader checks:

```bash
uv run pytest
uv run pytest -m integration
uv run pytest -m smoke
```

Smoke tests create a real OpenGL context.

## Build

```bash
uv sync --frozen
uv run python scripts/build_app.py
```

On macOS this produces `dist/Veilstone.app`; Windows and Linux produce a
`dist/Veilstone` directory. Packaged builds store settings, saves, and crash logs
in the platform user-data directory. `VEILSTONE_DATA_DIR` overrides the data
directory for automated tests.
