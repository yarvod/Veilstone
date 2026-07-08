# Changelog

## [Unreleased]

### Added

- **Render material metadata cache keys** - render layer now has pure material
  map role metadata and stable cache key inputs for future color/normal/specular
  material atlas work; Minecraft Java PBR sidecar discovery reuses the same
  sidecar role definitions. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_011413.png`.
- **Material atlas manifests** - generated block atlases now carry render-only
  material manifests discovered from Java-style PBR sidecars, cache schema v5
  persists them and invalidates older material-less caches without changing
  shader bindings. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_012024.png`.
- **Parallel material atlas builders** - render texture atlas code can now build
  CPU-side normal/material atlases aligned to existing color atlas dimensions,
  tile slots, UV rects, tile size, and edge inset metadata without binding extra
  shader textures by default. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_012541.png`.
- **Material sidecar image loading** - Minecraft Java resource-pack support now
  loads discovered PBR sidecar PNGs into role-keyed material tile maps so normal
  and material pixels can feed parallel material atlas builders while color
  atlas fallback behavior stays unchanged. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_012931.png`.
- **Material atlas bundles** - render texture atlas code now groups the existing
  color atlas with optional CPU-side material atlases, omitting absent roles and
  preserving aligned dimensions and UVs for present roles without binding extra
  shader textures by default. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_013212.png`.
- **Resource-pack material bundle assembly** - texture-pack importer now exposes
  a CPU-only helper that builds material atlas bundles from an already loaded
  color atlas and matching Java-style sidecar tiles, keeping the normal runtime
  color atlas path unchanged. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_013449.png`.
- **Material quality profile gate** - render layer now has a pure material
  pipeline decision helper that keeps default and low profiles color-only while
  naming an explicit `material-preview` opt-in path for future material atlas
  bundles. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_013727.png`.
- **Material quality settings plumbing** - graphics settings now persist
  `material_quality = "color-only"` and route it into the render material
  pipeline decision without assembling material bundles or binding extra shader
  textures by default. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_014247.png`.
- **Material profile debug visibility** - F3 debug snapshot text now reports
  the active material profile and whether material atlas bundles are enabled,
  keeping the default runtime visible as `color-only bundle off`. Real gameplay
  smoke screenshot: `saves/screenshots/veilstone_20260709_014603.png`.
- **Grass terrain material face contract** - block model snapshots now expose
  render-facing face material roles so tests lock grass top tint, untinted side
  base, dirt bottom, and grass-block item texture path separation before terrain
  smoothing work.
- **Atlas sampling metadata** - generated and cached texture atlases now expose
  tile size plus half-pixel edge inset metadata, with grass terrain UV tests
  locking sampling gutters before terrain smoothing work.
- **Distance-safe terrain atlas sampling** - chunk and shadow shaders now clamp
  repeated tile UVs by atlas edge inset metadata, reducing grass/terrain tile
  edge bleed without changing mesh layout. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_001923.png`.
- **Vegetation wind render metadata** - block model snapshots now classify
  visual-only wind motion for cross plants and cutout foliage while keeping
  solid grass blocks and non-plant cutouts static.
- **Render-only vegetation wind** - chunk mesh data and visible/shadow vertex
  shaders now apply subtle visual-only sway to cross plants and foliage through
  render-owned wind attributes and uniforms. Real checks: foliage OpenGL draw
  smoke and gameplay screenshot
  `saves/screenshots/veilstone_20260709_003639.png`.
- **Chunk meshing visual snapshots** - visible and greedy chunk mesh builders
  now consume atlas rect, render shape, and wind-motion lookups derived from
  `BlockModelSnapshot` instead of reinterpreting block visual texture fields
  directly. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_004550.png`.
- **Held item texture slot snapshots** - block item default/top/side/bottom
  texture policy now lives in shared texture-slot snapshots consumed by
  first-person viewmodel and existing inventory/entity/player held-item helper
  paths. Real OpenGL smoke: first-person viewmodel held-block draw.
- **PBR sidecar material reporting** - Minecraft Java resource-pack import now
  reports unsupported normal/specular/emissive/material sidecar maps
  deterministically while keeping the existing color atlas unchanged.
- **Reusable gameplay smoke screenshot route** - added
  `gameplay-smoke-screenshot` CLI command for deterministic walking/F3 runtime
  screenshots with JSON metadata. Real smoke passed with
  `saves/screenshots/veilstone_20260708_235956.png` and matching `.json`
  metadata.
- **F3 active resource-pack diagnostic** - debug overlay snapshots now include
  the active resource pack label and cover it in unit plus real `GameWindow`
  smoke checks. Runtime walking/F3 screenshot evidence:
  `saves/screenshots/veilstone_20260708_234722.png`.
- **Phase D architecture cleanup completed** - controller/HUD/runtime snapshot
  workplan is closed; active workplan now promotes Minecraft-like terrain
  visual polish and F3 diagnostics from `docs/BACKLOG.md`.
- **Grass/foliage tint model metadata** - render-facing block model snapshots
  now mark grass and foliage textures with tint kinds, establishing the typed
  path needed to tint Faithful-style grayscale vegetation assets.

- **HUD debug text snapshot** - F3 debug text assembly now routes through a
  `HudView` snapshot method instead of `HudController` reading chunk, renderer,
  entity, network, and settings state directly; focused HUD tests and real F3
  smoke screenshot `saves/screenshots/veilstone_20260701_004726.png` passed.

- **HUD player-list snapshot** - TAB player-list text now routes through a
  `HudView` snapshot method instead of direct HUD reads from network session
  state; focused HUD tests and real TAB smoke passed.

- **HUD remote-nameplate snapshot** - remote player nameplate render data now
  routes through `HudView` snapshots instead of direct HUD reads from network
  players and ECS transforms; focused HUD tests and real client smoke passed.

- **HUD debug selected/animation snapshot fields** - F3 selected-item and mob
  animation summaries now resolve inside the `HudView` debug snapshot instead of
  `HudController` reading hotbar, item registry, and ECS AI state directly;
  focused HUD tests and Pyright passed.

- **Narrower HUD view port** - `HudView` no longer exposes broad world,
  renderer, network, entity, hotbar, item-registry, or game-state objects to
  `HudController`; remaining HUD diagnostics route through snapshots.

- **Narrower input hotbar/debug ports** - `InputView` no longer exposes the
  debug shader or whole hotbar object for F-key, number-key, scroll, and
  placement input; those paths now use command/query methods with focused tests.

- **Narrower remote-player network ports** - `NetworkController` no longer
  mutates remote-player entity/interpolation dictionaries directly; remote
  entity lifecycle and movement updates now go through `NetworkView` commands.

- **Narrower gameplay resource-pack port** - `/resourcepack` command handling
  now calls a `GameplayView` resource-pack command instead of building the
  apply use-case from broad app-runtime/save-root fields inside the controller.

- **Narrower remote chunk request port** - `NetworkController` now asks
  `NetworkView` to request and track remote chunks instead of reading and
  mutating the requested-chunk set directly.

- **Narrower inventory drop ports** - `InventoryController` now routes hotbar
  selection and dropped-item spawn placement through `InventoryView` commands
  instead of depending directly on camera, player, and entity-world fields.

- **Input HUD/debug command ports** - F1 HUD visibility and F3 debug overlay
  toggles now route through `InputView` commands instead of direct window field
  mutation, with focused input tests and Pyright clean.

- **Reference gameplay scene CLI** - added deterministic `reference-gameplay-scene`
  fixtures covering water, foliage, lighting, mob movement, inventory icons, and
  first-person interaction, with numeric summaries and isometric capture
  metadata sidecar support. Real CLI smoke wrote
  `saves/screenshots/reference_gameplay_scene_20260701.json`.

- **Block/item model snapshots** - render-facing block/item model snapshots now resolve Minecraft-style texture ids for inventory icons, first-person held items, dropped items, and remote held items through one helper. Focused tests pass, real client smoke passed with F3/F5/inventory screenshot `saves/screenshots/veilstone_20260701_002605.png`, and movement/attack smoke moved the player `6.706` blocks with animation state `attack`.

- **Streaming scheduling helper** - chunk streaming, relight, and remesh queue budget drains now route through a pure render scheduling helper with focused tests; RD3 hidden frame-streaming smoke passed p95 `9.897 ms`.

- **Runtime perf debug snapshots** - added render-facing runtime performance snapshots for update/render timings and chunk/mesh queue depths; F3 now reads cached perf data and real HUD smoke passed with screenshot `saves/screenshots/veilstone_20260701_001314.png`. Hidden frame streaming smoke passed RD3 p95 `10.073 ms` and RD4 p95 `12.282 ms`.

- **HUD adapter cast wiring** - `GameWindow` now wires `HudController` through the same explicit `HudView` cast pattern as the other transitional window adapters.

- **UI hover callback typing cleanup** - `Widget` now owns an explicit optional hover callback and UI renderer callbacks are typed; focused UI renderer/widgets Pyright is clean.

- **Texture-pack report typing cleanup** - import reports now use typed string-list factories so focused texture-pack model Pyright stays clean.

- **Mesh worker typing cleanup** - section/chunk mesh worker task batches now carry explicit mesh-task/result types; focused worker Pyright is clean and hidden frame-streaming RD3 smoke stayed within p95 10.808 ms.

- **Menu UI world-list typing cleanup** - `MenuUI` now tracks saved worlds as `(name, Path)` tuples and keeps the focused menu UI Pyright gate clean while preserving real client startup smoke.

- **Controller-slice real smoke coverage** - D1 controller/input slices now have real app smoke coverage for `/resourcepack default`, Faithful apply/reset, F3 debug overlay, F5 perspective, F2 screenshot, inventory UI, LAN, and remote-render paths.

- **Input handler window adapter** - `InputHandler` now receives an `InputView` adapter with inventory/network input ports instead of reading `GameWindow` private controllers directly; F3/F5/F2 hidden-window smoke passed with screenshot `saves/screenshots/veilstone_20260630_204701.png`.

- **HUD inventory draw port** - `HudController` now renders hotbar, health, held item, and inventory UI through `InventoryHudPort` instead reading `GameWindow._inv_ctrl`; focused HUD Pyright is clean and F3 debug-overlay screenshot smoke passed at `saves/screenshots/veilstone_20260630_203815.png`.

- **Network controller window adapter** - `NetworkController` now receives a `NetworkView` adapter instead of the full `GameWindow`; Open-to-LAN and remote-render integration smoke tests pass after forwarding adapter writes.
- **Inventory controller window adapter** - `InventoryController` now receives an `InventoryView` adapter instead of the full `GameWindow`; unit inventory/input tests and real client inventory smoke passed.
- **Gameplay controller window adapter** - `GameplayController` now receives a `GameplayView` adapter instead of the full `GameWindow`; real client smoke startup passed after the wiring change.
- **Gameplay controller typing guards** - command handling now guards local player/entity access and texture-pack service wiring, making `render/gameplay_controller.py` focused-Pyright clean while D1 controller-port extraction continues.
- **Bounded render-distance streaming** - chunk submission, relight work, and remesh scheduling now use per-frame budgets; the frame-streaming benchmark can run synthetic moving-player profiles with render-distance and warmup controls.
- **Distant world readability coverage** - terrain generation now uses registry
  biome base heights for stronger highland/plain/swamp silhouettes, with
  deterministic distant landmark density coverage for ruins, camps, and spires.
- **Inventory presentation snapshots** - item count text, tooltips, cursor labels,
  and crafting result feedback now come from application-level presentation
  snapshots instead of render UI duplicating inventory/item rules. Real-game
  inventory smoke screenshot: `saves/screenshots/veilstone_20260630_164513.png`.
- **Mob animation state and contact phase** - cow/zombie locomotion now separates
  idle, walk, attack, hurt, and death poses; blocked mobs stop advancing foot
  phase; future footstep sounds can use the same contact phase as rendering.
  Real-game smoke screenshot:
  `saves/screenshots/veilstone_20260630_163807.png`.
- **Mob locomotion animation phase** - mob walk animation phase now advances
  from actual grounded horizontal velocity instead of raw frame time, with tests
  for moving, idle, and blocked-displacement cases.
- **Water surface smoothing** - water mesh generation now smooths top vertices
  across neighboring fluid levels without changing voxel simulation rules,
  covered by unit geometry checks and real-game screenshot smoke
  `saves/screenshots/veilstone_20260630_124156.png`.
- **Water shore movement coverage** - player physics tests now lock down swim
  buoyancy, slow sinking, shore step-up, and collision against taller shore
  walls, with runtime smoke coverage against `GameWindow` world blocks.
- **Water fluid correctness coverage** - water unit tests now lock down
  cross-chunk level propagation and dirty mesh/save flags before render-side
  flow smoothing work.
- **Minecraft-style bundled content routing** - entity textures and gameplay
  sounds now live in `resource_packs/default/assets/<namespace>/...`, while
  configs reference them with resource locations instead of legacy
  `assets/audio` / `assets/entities` paths.
- **Player landing and splash audio events** - player landing and water
  enter/exit transitions now publish gameplay events that the audio bridge maps
  to tuned movement sounds.
- **Local player avatar shadows** - third-person local player avatars now share
  the entity shadow pass with remote/player entities, covered by OpenGL smoke
  coverage and real-game visual screenshot verification.
- **Bundled default resource pack** - Veilstone now ships an original Minecraft-like `resource_packs/default` Java-style pack and uses it for default atlas loading and missing-texture fallback before procedural tiles.
- **Shared player avatar render adapter path** - remote player entities now apply
  `PlayerRenderSnapshot` through the same avatar render adapter used by the
  local third-person player, preserving yaw, held items, animation phase, and
  stale held-item cleanup without duplicating model component wiring.
- **Remote player interpolation coverage** - multiplayer remote player entities
  now have controller-level regression coverage proving delayed snapshots update
  rendered transforms through interpolation instead of snapping directly.
- **Remote player nameplate render path** - HUD nameplates now consume the
  player nameplate snapshot/render adapter, including distance visibility,
  sanitized fallback names, and alpha fade in the live label draw path.
- **Player entity render snapshot metadata** - player render snapshots now carry
  head pitch, display name, health, max health, and status flags so local and
  remote player presentation can converge without reading raw `GameWindow`
  state.
- **F3 device and cached telemetry diagnostics** - debug overlay now includes
  renderer device/version information and caches slow runtime/memory telemetry
  separately from fast FPS/position updates.
- **Settings Development graphics menu** - smooth lighting, ambient occlusion,
  fog, and mesher comparison toggles now live in Settings -> Development and
  persist through user settings instead of relying on hidden F-key bindings.
- **Minecraft-feel architecture guardrail** - active workplan now requires new
  visual/UI/audio/network/gameplay slices to avoid adding state or orchestration
  to `GameWindow`, with full `GameWindow` decomposition tracked in backlog.
- **Block interaction feedback event** - block breaking and placing now publish
  a shared interaction-start event before completion events, so viewmodel swing,
  future particles, audio, and network presentation can share one gameplay
  hook instead of observing raw input separately.
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
- **Developer-only graphics controls** - graphics renderer toggles moved out of
  plain `F6`-`F9` bindings and now live in Settings -> Development, keeping
  function keys focused on player-facing controls.
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

- **Water mesh startup crash** - water chunk meshes now bind 15-float
  transparent mesh layouts without vegetation-only `in_wind_motion` for visible
  and depth VAOs, fixing ModernGL VAO creation when water is rendered. Real
  checks: water VAO hidden-window smoke
  `saves/screenshots/veilstone_20260709_010942.png`, gameplay walking smoke
  `saves/screenshots/veilstone_20260709_011009.png`, current gameplay smoke
  `saves/screenshots/veilstone_20260709_014932.png`.

- **Windows entity animation unit test** - remote-player texture path assertions now
  normalize paths with POSIX separators, matching cow and zombie checks on
  Windows CI.
- **Short grass lighting** - crossed plant meshes now sample light from their
  own cell and the air above, preventing grass and flowers from turning nearly
  black because of shifted halo light samples.
- **Texture-pack apply shadows and labels** - Texture Packs now shows a single
  canonical `Default`, local Java-style packs such as Faithful are not labeled
  legacy, cached non-default packs report their own name, and applying packs
  preserves chunk shadow-depth meshes.
- **F3 debug overlay first-frame visibility** - debug diagnostics now populate
  immediately when F3 is enabled, so FPS, position, chunk, biome, memory, and
  mesh stats are visible in the real game window without waiting for a later
  throttled HUD refresh.
- **Readable cutout plant shadows** - terrain shadow sampling now preserves
  center shadow-map hits so thin alpha-tested grass/foliage casters are not
  blurred away by receiver filtering, making nearby plant shadows visible.
- **Fuller cutout and mob shadow casters** - chunk/entity shadow-depth rendering
  now disables face culling so crossed grass planes and all cuboid mob parts can
  write complete silhouettes into the shadow map.
- **Readable world shadows and grass tint** - chunk shadows now read darker in
  daylight without over-darkening ambient light, imported Minecraft-style grass
  and leaves use a lighter plains tint, and default grass fallback colors are
  brighter.
- **Dropped item gravity** - ECS item drops now receive small physics
  components and fall when the supporting block below them is removed.
- **Cutout plant shadows and atlas seams** - chunk shadow depth now respects
  atlas alpha cutouts, world block atlases use clamped nearest sampling without
  mipmap bleeding, and chunk shaders no longer randomly flip atlas tiles between
  neighboring blocks.
- **Grass plant rendering polish** - default short grass now uses sparse
  bottom-rooted cutout blades without opaque texture borders, cross-plant quads
  use top-biased lighting, and chunk texture variation no longer vertically
  flips rooted resource-pack plant textures.

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
