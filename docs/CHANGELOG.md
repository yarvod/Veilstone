# Changelog

## [Unreleased]

### Added

- **Debug overlay runtime diagnostics** - F3 debug overlay now includes Python
  runtime/platform and current frame size alongside existing chunk, mesh, entity,
  network, and coordinate counters.
- **Product backlog** - added a dedicated backlog for multiplayer spawn/streaming
  failures, grass/resource-pack rendering defects, F3 diagnostics gaps, and
  render-distance performance work.
- **Expanded F3 diagnostics** - F3 now reports FPS, frame time, facing, biome,
  memory estimate, render distance, and mesh upload budget alongside existing
  coordinates, chunk, mesh, entity, network, runtime, and selection data.
- **Safe staged update installer** - the Updates screen can now prepare and
  launch an external installer script for downloaded release zips; the script
  waits for the running app to exit, swaps the app bundle/folder, cleans the
  backup, and restarts Veilstone without touching app-data saves/settings/packs.
- **In-app update screen** - Settings now includes an Updates screen that lists
  GitHub releases, marks current/prerelease/platform availability, and downloads
  the selected platform zip into the app-data updates staging directory without
  touching saves.
- **Background update tasks** - in-app update checks/downloads now run on a
  background worker and report staged download progress through the menu status.
- **Cancellable update downloads** - update downloads can be cancelled from the
  Updates screen, and partial staged archives are cleaned up on cancellation or
  progress callback failure.
- **Release/update tooling** - added version metadata, release scripts, GitHub tag release packaging with platform zip assets, and CLI update check/download staging through GitHub Releases.
- **Release tag repair mode** - release scripts can now move an existing
  remote tag to the current fixed commit with `--replace-tag` / `--retag`,
  guarded by current-version checks and tag `--force-with-lease`.
- **Biome ground cover** - terrain generation now places deterministic cutout
  tall grass and wildflowers across plains, woods, and swamp biomes with
  resource-pack mappings and density coverage.
- **Render-distance settings control** - Settings now exposes `[world].render_distance`
  as a cycling menu value and persists changes to user settings.
- **Walk/sprint cadence coverage** - added regression coverage for gait-phase
  footstep contact timing so sprint steps remain faster than walking steps.
- **Transparent foliage smoke scene** - added a reusable cutout-leaf fixture,
  CLI preview, unit coverage, and an OpenGL-gated runtime smoke path for leaves
  in front of an opaque backdrop.
- **Resource-pack cutout verification** - added Faithful oak-leaf alpha coverage
  through the real block-atlas importer and documented supported vs planned
  resource-pack features.
- **Per-material footstep sound keys** - walking now resolves to `step.*`
  material sounds before falling back to `footstep`, leaving `block.*` sounds
  available for louder breaking/placing actions.
- **Inventory drag-and-drop movement** - inventory stacks can now be picked up,
  dragged to another slot, and dropped there with a distinct drag-target slot
  highlight, covered by unit tests and the real inventory smoke path.
- **Debug HUD diagnostics** - F3 overlay now includes block/chunk coordinates,
  network mode, remote-player counts, selected item, and existing chunk/entity
  render metrics in the real HUD draw path.
- **Cutout foliage rendering** - leaves can now be marked as cutout blocks in
  block data, procedural leaf textures include transparent holes, and the chunk
  shader discards transparent atlas texels so foliage holes reveal the world.
- **Inventory hover presentation** - inventory and crafting slots now highlight
  on hover and draw a Minecraft-like item-name tooltip with stack count through
  the real HUD draw path.
- **Remote player held-item replication** - LAN player snapshots now carry
  compact held-item payloads into remote player ECS components, so other players
  can render selected blocks/items in hand without network render objects.
- **Player avatar held-item rendering** - entity rendering now draws a small
  animated held block/item cuboid attached to player avatar arm pose data.
- **Player avatar held-item snapshot data** - local third-person player render
  snapshots now carry selected held item data into a dedicated ECS component for
  the shared player model path.
- **Player nameplate snapshots** - added application/render data for remote
  player nameplates above character heads with distance fade visibility rules.
- **Developer-only graphics F-key toggles** - graphics renderer toggles moved
  from plain `F6`-`F9` to `Ctrl+F6`-`Ctrl+F9`, keeping normal F-keys free for
  player-facing controls.
- **Screenshot shortcut** - `F2` saves a PNG screenshot under the user data
  screenshots directory.
- **HUD visibility shortcut** - `F1` now toggles HUD visibility at runtime.
- **Perspective cycling** - added first-person, third-person-back, and
  third-person-front camera modes; `F5` cycles perspective and `Ctrl+F5` keeps
  shader reload as a development shortcut.
- **Viewmodel interaction swings** - attack, block break, and block place inputs
  now start player interaction animation state, driving the first-person
  viewmodel swing pose.
- **First-person viewmodel renderer MVP** - added a small ModernGL cuboid
  overlay renderer for the first-person hand and selected held item, driven from
  viewmodel snapshots and rendered before HUD.
- **First-person viewmodel render adapter** - added render-facing cuboid part
  data for the hand and held item from the application viewmodel snapshot.
- **First-person viewmodel snapshot** - added application-layer hand/held-item
  pose data with bob and interaction swing offsets so the renderer can add a 3D
  hand without reading raw window or inventory state.
- **Gait-driven camera bob** - local camera height now reads bob offset from the
  player animation snapshot instead of a separate render-owned `HeadBob`
  oscillator.
- **Gait-driven local footsteps** - `GameWindow` now advances player animation state each update and emits local footstep sounds from gait contact snapshots instead of a separate footstep accumulator.
- **Player animation state foundation** - added application-layer gait and interaction animation state/snapshots for walk, sprint, swim, footstep contact, camera/viewmodel bob values, and interaction progress without Pyglet/OpenGL.
- **README current-state refresh** - README now describes the actual prototype feature set, known gaps, controls, settings, architecture direction, and roadmap docs instead of carrying old phase-by-phase manual test history.
- **Gameplay-feel roadmap** - `WORKPLAN` now tracks the next immersion work: viewmodel/held item animation, gait-synced footsteps, water shore exit and surface polish, mob locomotion, leaf transparency, inventory item presentation, generation richness, debug/perspective controls, and Minecraft-like time semantics.
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

- **Short grass block silhouette** - short grass and wildflowers now use a
  data-driven crossed plant mesh instead of full cube cutout faces, reducing the
  green cage/cube appearance in default and Minecraft-style resource packs.
- **Packaged app data registries** - release builds now include `data/`
  registries, package verification checks them, and wheel package resources
  include data fallbacks so startup no longer fails on missing `data/items.toml`.
- **Camera position setter regression** - `FirstPersonCamera.position` can be set
  as a tuple again, fixing the transparent foliage OpenGL smoke scene.
- **Prerelease release tags** - release version tooling now accepts
  PEP 440-compatible tag suffixes like `v0.0.1-beta1`, preserves the original
  Git tag, and sanitizes package zip names without dots or build symbols.
- **Release version script idempotency** - releasing the already-current version
  no longer reports `project.version` as missing.
- **Windows CI UI tests** - UI renderer tests now skip when the runner exposes a
  display without shader-capable OpenGL, avoiding `glCreateShader` failures on
  package builds.
- **Faithful grass side overlay** - Minecraft Java grass side textures now
  composite the biome-tinted `grass_block_side_overlay` layer and invalidate
  older texture-pack atlas caches.

- **Faithful grass and held block textures** - held block viewmodels now use the
  same top/side/bottom texture faces as placed blocks, Faithful grass/leaves
  receive Minecraft-style biome tint during atlas import, vanilla-like keys such
  as `grass_block`/`lantern` are aliased, and lantern blocks render in the
  cutout layer instead of opaque black cubes.
- **First-person held lantern silhouette** - removed the temporary torch-like lantern handle model so held block items render as compact blocks instead of a second rod beside the arm.
- **Dedicated server default save path** - omitted `server --world` now uses the Veilstone application data root instead of a relative install-directory path.
- **New-world inventory UI state** - inventory logic now refreshes its active
  inventory reference after world creation or switching, preventing stale saved
  stacks from appearing through UI interactions in a new world.
- **Fullscreen framebuffer sizing** - rendering now uses framebuffer dimensions for ModernGL viewports, so fullscreen/Retina windows no longer leave the game/menu clipped into a lower-left rectangle.
- **New-world defaults** - new worlds now start with an empty hotbar/inventory and a bright late-sunrise morning instead of debug items at dusk/night.
- **Footstep sound harshness** - regenerated softer local footstep/block-step WAVs and lowered their default gains so walking is quieter and less abrasive.

- **Local player avatar yaw** - local third-person player model yaw now converts
  camera-facing degrees into the radians-based ECS/entity renderer transform.
- **First-person hand duplication** - legacy 2D HUD hand/item overlay is now
  disabled; first-person presentation uses only the 3D viewmodel.
- **Held block viewmodel texture** - first-person held block cuboids now resolve
  their texture from the selected item/block registry and render with atlas UVs.
- **Local third-person player gait** - local player avatar rendering now receives
  the same gait animation phase used by camera bob, footsteps, and viewmodel
  motion, reducing static sliding when perspective is switched.
- **User world settings persistence** - user settings writes now include the
  `[world]` section, including render distance and generation/meshing settings.
- **World create/delete persistence** - creating a world now chooses a unique
  save directory instead of reusing an existing slug, preventing old player
  inventory from leaking into new worlds; deleting a world now invalidates the
  saved-world cache.
- **Perspective initialization crash** - `GameWindow` now initializes perspective
  mode before the first camera sync during startup.
- **Water shore exit** - player physics now supports swimming/jumping out of
  water onto a one-block shore via a bounded collision step-up, covered by a
  regression test.
- **Time command semantics** - `/time set day` now means sunrise/start of day; `noon` remains the high-sun value.
- **Default day cycle length** - default graphics day/night cycle now uses 1200 seconds, matching a Minecraft-like 20-minute full cycle.
- **Footstep loudness** - default block-step and fallback footstep gains are lower in `config/audio.toml`.
- **Resource pack application regression** - `ApplyResourcePackUseCase` now receives the block registry explicitly instead of reading `renderer.registry`, so resource packs still apply after renderer/world ownership split.
- **Display-less UI interaction tests** — `test_ui_interaction.py` now skips at module level when no active display exists instead of failing during Pyglet window import/GL setup.
- **Display-less unit collection** — key/mouse constants now have a fallback-safe import path, so input and inventory unit tests do not fail collection when no Pyglet display is available.

### Changed
- **GitHub Actions runtime dependencies** - package workflow now uses Node
  24-compatible action releases for checkout, uv setup, artifact transfer, and
  GitHub Release publishing without the old force-Node env override.
- **Named time command contract** - README and command tests now document the
  exact Minecraft-style tick values for `/time set` names, numeric wraparound,
  and the `twilight` preview freeze behavior.
- **Resource pack storage root** - texture pack imports now target app-data
  `resource_packs/`, while legacy local `resource_packs/` remain discoverable,
  so app updates do not overwrite user packs.
- **First-person arm proportions** - shortened the blue sleeve into a cuff and
  made the skin hand/forearm the dominant cuboid so the viewmodel no longer
  reads as two separate rods.
- **Vanilla block keys** - oak log/leaves/planks, crafting table, and short grass
  now use Minecraft-like canonical registry keys while keeping legacy Veilstone
  aliases for existing saves, structures, recipes, and tests.

- **Minecraft-like time semantics** - `/time set day` now targets early bright day,
  `sunrise` remains the horizon, and atmosphere daylight uses explicit
  dawn/day/sunset/night keyframes so new-world late sunrise reads bright.
- **First-person hand silhouette** - widened and tightened the sleeve/hand
  cuboids so the viewmodel reads as one connected Minecraft-like arm instead
  of two separated rods.
- **Live render-distance apply** - changing render distance in Settings now
  updates active chunk streaming immediately while still saving user settings.
- **First-person viewmodel gait sway** - first-person hand and held item pose
  now uses deterministic lateral and forward sway from gait phase, with stronger
  sprint motion and mirrored left-hand movement.
- **First-person hand model polish** - first-person viewmodel now renders a blocky sleeve and skin hand as separate cuboids, attaches held blocks/items to the hand, and has smoke coverage for the runtime first-person draw path.
- **First-person viewmodel pose** - adjusted the MVP viewmodel from centered debug cuboids to a single lower-right arm, with held blocks attached to the hand and a torch-like lantern model for the lantern item.
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
