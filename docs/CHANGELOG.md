# Changelog

## [Unreleased]

### Added

- **3D player debug draw path** - added `development.render_local_player_model` toggle and optional local player avatar rendering through the existing entity renderer path.
- **3D player render adapter** - added CPU-side player avatar adapter mapping `PlayerRenderSnapshot` into existing entity renderer transform/model data.
- **3D player snapshot** - added `PlayerRenderSnapshot` application view data and tests so a future player renderer can consume player state without depending on Pyglet/ModernGL.
- **Generation guard tests** - generation feature densities and hardcoded feature block IDs are now checked against expected probability ranges and block registry data.
- **Generation decorators** - terrain generation now includes dungeon and Dusk Highlands pillar decorators, plus deterministic tests for Twilight Woods mushrooms/fireflies and Gloom Swamp glowing mushrooms.

- **Water improvements (Phase B2)** — water now flows across chunk boundaries; two adjacent source blocks fill the gap with a new source block (infinite water mechanic); all loaded chunks are ticked together each 0.2 s step instead of one at a time, so a lake across multiple chunks propagates at full speed.

- **Player feel overhaul (Phase B1)** — coyote time (0.12 s), jump buffering (0.12 s), variable jump height (release Space while rising for a shorter arc), sprint (Shift → 8 m/s, faster footstep cadence), and subtle head bob camera oscillation when walking.

- **Phase A architecture stabilization closeout** - `WORKPLAN` now marks A4/A5/A8/A9 completed; app runtime owns texture-pack service wiring and isolated subsystem test coverage was audited.
- **AppRuntime texture-pack service** - `build_app_runtime()` now wires `RenderTexturePackService`, removing the remaining texture-pack service construction from `GameWindow`.
- **DemoWorldRenderer ownership fields private** - storage, registry, generator, and streamer are no longer public renderer fields after external callers moved to runtime context.
- **Inventory runtime block registry** - inventory item icon setup now uses `world_runtime.block_registry`; external callers no longer reach into `world_renderer.storage/registry/generator/streamer`.
- **InputHandler runtime block registry** - mining fluid checks now use `world_runtime.block_registry` instead of direct renderer registry access.
- **GameplayController runtime world reads** - population and hazard checks now read terrain generation/block registry through `world_runtime` instead of renderer-owned fields.
- **GameWindow runtime world accessors** - window-local registry, terrain generator, and chunk streamer reads now go through runtime accessors instead of direct renderer fields.
- **NetworkController runtime storage** - LAN structure save/load and local authority startup now use `world_runtime.storage`; added focused unit coverage for local authority structure loading.
- **WorldManager runtime storage** - world switching and player save/restore now use `world_runtime.storage` instead of reaching through `world_renderer.storage`.
- **WorldRuntime init callers** - initial player restore, structure world loading, and structure renderer registry wiring now read from `world_runtime` instead of direct renderer-owned world fields.
- **World runtime rebuild context** - `GameWindow._rebuild_world_runtime()` now reads storage, registry, generation, and streaming from the current `WorldSceneDependencies` context instead of treating the renderer as the source of ownership.
- **World scene dependency builder** - storage, block registry, terrain generator, and chunk streamer construction now lives behind `build_world_scene_dependencies()` and is passed into `DemoWorldRenderer`.

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
- **ApplyResourcePackUseCase** — added an application use case with explicit render/settings ports and routed `/resourcepack` command handling through it.
- **Texture pack UI use case wiring** — Settings Texture Packs apply now routes through the same `ApplyResourcePackUseCase` as `/resourcepack`, preserving UI import report status.
- **Texture pack service port** — resource pack discovery/loading/cache access now goes through a texture pack service port with a render adapter, keeping command/UI paths off direct importer/discovery functions.
- **Stronger architecture guardrails** — import-linter now also enforces that `engine` does not import `render`, and `application` does not import Pyglet or ModernGL.

### Fixed

- **Resource pack application regression** - `ApplyResourcePackUseCase` now receives the block registry explicitly instead of reading `renderer.registry`, so resource packs still apply after renderer/world ownership split.
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
