# Changelog

## [Unreleased]

### Added

- **Architecture stabilization plan** — added `docs/ARCHITECTURE.md` with current dependency map, target layers, composition root strategy, ports/adapters, GameWindow/controller migration, DemoWorldRenderer split, and staged import-linter contracts.
- **Architecture guardrail** — configured import-linter in `pyproject.toml`; `uv run lint-imports` now enforces that `voxel_sandbox.domain` does not import external adapter layers.
- **Manual composition skeleton** — added `AppRuntime` and `WorldRuntime` dataclass contexts in `app/composition.py` for future wiring extraction.
- **AppRuntime factory** — added `build_app_runtime()` with app-level settings store, data root, event bus, audio bus/director, and item registry composition, covered by unit tests.
- **GameWindow AppRuntime compatibility path** — `GameWindow` can now receive an `AppRuntime`; if omitted, it builds one through the composition factory while preserving existing constructor behavior.
- **WorldRuntime map** — added `build_world_runtime()` and attached `GameWindow.world_runtime` to record active world storage, registry, generation, streaming, player, entity world, and renderer dependencies as the next migration point.
- **Local world runtime builder** — player and entity simulation construction now goes through `build_local_world_runtime()`, with existing `GameWindow.player` and `GameWindow.entities` fields kept as compatibility aliases.
- **WorldRuntime switch refresh** — world switching now rebuilds the runtime context through the same local world runtime path, keeping player/entity compatibility fields synchronized after loading or creating worlds.
- **HudController dependency boundary** — HUD rendering now depends on an explicit `HudView` Protocol instead of the nominal `GameWindow` type, starting the controller migration away from `Controller(GameWindow)`.
- **HUD window adapter** — `GameWindow` now passes `HudWindowAdapter` into `HudController`, localizing the remaining window compatibility surface behind explicit HUD-facing properties.
- **HUD frame snapshot** — HUD frame/layout reads now use `HudFrameSnapshot` for width, height, and inventory-open state instead of direct window field reads.

### Fixed

- **Display-less UI interaction tests** — `test_ui_interaction.py` now skips at module level when no active display exists instead of failing during Pyglet window import/GL setup.
- **Display-less unit collection** — key/mouse constants now have a fallback-safe import path, so input and inventory unit tests do not fail collection when no Pyglet display is available.

### Changed

- **Agent instructions merged** — `CLAUDE.md` and `AGENTS.md` now contain the same complete project instructions, including RTK usage, docs workflow, checks, architecture rules, and commit policy.
- **Workplan reset** — `docs/WORKPLAN.md` now tracks only the active Architecture Stabilization phase and next actions; completed historical phase checklists were removed from the active plan.
- **Bug tracker reset** — `docs/BUGS.md` now tracks active issues/watchlist only instead of resolved historical bug entries.

## Historical Completed Work

### Architecture and Extensibility

- Extracted major `GameWindow` responsibilities into focused controllers/managers including inventory, input, network, world management, gameplay command handling, menu UI, and HUD.
- Added gameplay `EventBus` and connected block/entity events to audio.
- Added world generation pipeline protocols and `DimensionDef`; biome surface placement reads block IDs from registries.
- Added `GameState` / `GameStateMachine` for menu, playing, and paused transitions.
- Extracted gameplay constants from scattered magic numbers.

### Data and Resource Packs

- Moved blocks, biomes, and items toward data-driven TOML registries.
- Added Minecraft Java-style resource pack MVP using `minecraft:block/*` resource locations.
- Added folder/ZIP pack reading, runtime `/resourcepack <path|default>` apply, UI texture-pack picker, fallback textures, and atlas cache invalidation.

### Gameplay Fixes

- Added player swimming, water passability, and water flow/drain behavior.
- Fixed block breaking through water via fluid-skipping raycast.
- Fixed mob spawn validation, water movement jitter, obstacle avoidance, zombie height checks, and attack animation reset.
- Fixed saved-world loading after MenuUI extraction, world-list ordering, menu hover sound looping, and structure command key naming.

## Format

- `Added` — new features or capabilities.
- `Changed` — meaningful changes to existing behavior, tooling, or process.
- `Fixed` — bug fixes.
- `Removed` — removed user-visible behavior or major internal components.
