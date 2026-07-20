# Changelog

## [Unreleased]

### Fixed

- **Selection-highlight false positive closed** - the apparent translucent
  diagonal bands in the N11 F2 continue across neighboring terrain and are not
  selection geometry. The highlight has no filled faces: focused coverage now
  locks its 12 unique cube edges and `moderngl.LINES` draw primitive. The N11 and
  current visible N16 F2 captures were rechecked from distinct selected-face
  perspectives; a fresh visible two-angle session was blocked by macOS exposing
  no active Pyglet screen.
- **Continuous biome ridges and clustered highland formations** - registry-
  driven terrain now blends biome base height and variation from smooth climate
  weights instead of switching elevation profiles at the discrete surface-biome
  boundary. Dusk Highlands ore landmarks use sparse deterministic cells with a
  stepped circular footprint and one crown, including consistent cross-chunk
  placement. The former flat stone wall is now a readable terraced slope in
  `saves/terrain_n16/rd12_1800_highlands.png`; nearby formation and visible F2
  evidence live under `saves/terrain_n16/`. A 1800-frame paced RD12 walk measured
  p95 `9.403 ms`, p99 `10.422 ms`, max `17.801 ms`, with every queue drained.
- **Display-less GL capability preflight** - test support now checks for an
  active Pyglet screen before importing `pyglet.gl`, preventing its implicit
  shadow window from reaching a Cocoa destructor crash when `screens=0`.

- **Bounded streaming unload persistence** - walking across an RD12 chunk border
  no longer compresses and writes all 25 departing dirty chunks in one update.
  Deferred saves drain one per frame and an unsaved chunk can return directly if
  the player reverses direction; restart persistence remains covered.

- **Order-independent Pyglet UI renderer tests** - UI widget tests now keep an
  explicitly owned hidden GL context alive for their module lifetime, so an
  earlier test disabling the Pyglet shadow window can no longer leave
  `pyglet.gl.current_context=None`. The shortest failing order now passes `13`
  tests and the complete render group passes `122`; production UI behavior and
  display-less skips are unchanged.
- **Fresh-launch first-click reliability on macOS** - the native Pyglet view now
  accepts the first activating mouse click, so menu controls no longer require a
  second click when the window starts or regains focus. The fix stays at the
  Cocoa boundary and preserves the existing one-press/one-release widget path.
  Four independent visible cold launches, split evenly with and without initial
  pointer motion, each recorded exact action counts `1,1,1,1,1` across
  Settings/Back, Singleplayer/Cancel, and pause/Resume; Resume recaptured the
  mouse and first motion changed yaw by `2.8800` degrees.
- **Stuck movement after pause** - Escape now clears held movement/sprint state
  before entering the pause menu, so a release event lost during the transition
  cannot resume movement later. The visible lifecycle pass measured `0.0000`
  drift after ordinary release and after two Resume cycles while also confirming
  inventory and focus transitions clear input.
- **Mouse Resume capture** - clicking `Resume` now synchronizes game state and
  exclusive mouse capture after the menu target changes to gameplay, matching
  keyboard activation instead of leaving the pointer visible and the camera
  inactive.
- **Single-item right-click pickup parity** - right-clicking a single inventory
  item now moves it onto the cursor and clears the source slot, matching the
  crafting-grid path. Empty slots remain no-ops, while odd/even ceil-half
  behavior and drag placement remain covered. Focused domain/UI/Input coverage:
  `103 passed`; full unit gate: `763 passed`, `10` display-dependent skips. The
  real-GL integration is included but skipped while Pyglet reports `screens=0`.
- **Odd-stack right-click split parity** - `Inventory.split()` now takes the
  ceil-half of odd stacks, so `5` becomes cursor `3` plus source `2`, matching
  crafting-grid and Minecraft behavior; even stacks and the scoped single-item
  no-split behavior remain unchanged. Domain/UI/Input focused coverage:
  `101 passed`. The new GL integration is included but skipped because Pyglet
  still reports `headless=false, screens=0`.
- **Transactional inventory quick-move routing** - Shift-click between hotbar
  and main inventory now merges matching stacks first and then uses empty slots,
  skipping incompatible targets instead of calling swap-capable
  `Inventory.move()`. Destination exhaustion preserves the original source item
  and remainder. Focused routing/input coverage: `94 passed`; full unit gate:
  `758 passed`, `10` display-dependent skips. A real-GL integration case is
  included but the final rerun was unavailable because Pyglet reported
  `headless=false, screens=0`; the macOS environment also lacks headless `EGL`.
- **Inventory action feedback priority** - a pure presentation resolver now
  prefers fresh explicit inventory actions over derived recipe warnings, while
  still showing `No matching recipe` when no action message exists. Ordinary
  slot/crafting clicks clear stale actions. The K6 mixed-capacity scene now
  visibly renders `Distributed Stone x7 across 3 slots.`:
  `saves/inventory_feedback_smoke_k7/screenshots/distribution_action_visible.png`,
  metadata `saves/inventory_feedback_smoke_k7/inventory_feedback_smoke.json`.
- **Softer terrain shadow filtering** - chunk color-only and material-preview
  receivers now use a 5x5 PCF average with a softer shadow floor, reducing hard
  triangular/blocky terrain shadow artifacts while preserving actual occluder
  shadows. Real after-fix smoke:
  `saves/shadow_preset_smoke_after_fix/medium/screenshots/veilstone_20260709_155439.png`,
  `saves/shadow_preset_smoke_after_fix/high_material_preview/screenshots/veilstone_20260709_155441.png`.
- **Dropped item water buoyancy** - item drop physics now targets the water
  surface instead of repeatedly switching between upward water velocity and
  gravity, so drops rise to the surface and settle with minimal jitter. Unit
  coverage locks stable item-in-water buoyancy; real item-water smoke:
  `saves/item_water_smoke/screenshots/veilstone_20260709_152329.png`
  (`item_y=89.860`, `item_vy=-0.002`, `last_jitter=0.0007`).

- **Preset/material quality ownership** - explicit `/materials` or Settings material
  toggles now return graphics quality to `custom`, so `high`/`cinematic` presets
  do not silently reapply `material-preview` after a renderer rebuild or restart.
- **No-shadow chunk sampler binding** - world chunks now bind a neutral 1x1 depth
  texture on shadow texture unit when shadows are disabled, avoiding Metal/OpenGL
  sampler warnings in `low_60` while keeping real shadow maps unchanged. Real
  smokes: `low_60`
  `saves/profile_smoke_low_60/screenshots/veilstone_20260709_144744.png`,
  `high` material-preview
  `saves/profile_smoke_high/screenshots/veilstone_20260709_144753.png`.

### Added

- **RD12 low-end rendering pipeline** - the production-world standalone CGL
  benchmark can now wait for all 625 radius-12 chunks, profile update work,
  split render submission from GPU wait, report stage timing/draw calls, pace
  asynchronous workers at real 60 Hz, and capture a final PNG. Streaming work
  is frame-coalesced and budgeted; mesh replacements retain only the latest
  request; background generation/meshing processes yield OS priority to the
  frame owner. Fog-range AABB culling plus per-chunk vertical GPU batches reduced
  a fully loaded 600-frame 1280x720 `low_60` walk on Apple M4 to p95 `6.235 ms`,
  p99 `9.411 ms`, max `15.918 ms`, with `26` final draw calls and every queue
  drained. Inspected production-CGL frame:
  `saves/perf_rd12_n15/rd12_low60_acceptance_nice.png`. Physical two-core and
  visible UI acceptance remain open.
- **Optional native performance kernels** - Hatch/Cython now builds packaged
  greedy-rectangle and sparse-light extension modules with typed array APIs,
  `.pyi` contracts, and deterministic Python fallbacks. Full section meshing
  improved about 11%, sparse light propagation about 5.1x; dense skylight is
  intentionally dispatched to faster NumPy. A clean wheel install loads both
  extension modules. Final gates: import contracts/Ruff/format green, `877
  passed, 38 skipped`, focused Pyright `0`, full known-red baseline `389`.
- **Terrain atlas sampling polish** - color and material atlases now extrude
  one-pixel gutters with cache-versioned UVs. Balanced and higher world terrain
  uses linear minification plus nearest magnification, while `low_60`, held
  items, and CPU inventory icons remain pixel-sharp. Standalone production
  shader comparison showed no adjacent-tile bleed; visible F2 acceptance is
  still blocked while Cocoa reports no active screen.

- **Low-end frame benchmark contract** - `benchmark-frame-streaming` now accepts
  explicit framebuffer size, quality preset, worker allocation, movement path,
  speed, and startup timeout; it waits for loaded visible geometry before
  timing and reports p50/p95/p99, resolved effects, bottleneck distribution,
  and queue start/max/end so an empty frame or growing backlog cannot pass.
  The realistic 1280x720 walk with one generation and one meshing worker loaded
  `25` chunks/`43` visible sections: p95 was `4.052 ms` for `low_60`, `4.139 ms`
  for `balanced`, and `4.220 ms` for `high` on the M4 host. A 15-second
  `low_60` run measured p95 `4.859 ms`, p99 `8.047 ms`, max `17.556 ms`, with
  mesh queue `0 -> 60 -> 0`. The visible W/F3/F2 pass moved `15.0` blocks and
  finished with every streaming/mesh queue at zero; inspected frame:
  `saves/low_60_n13_final/screenshots/veilstone_20260720_101305.png`. Physical
  two-core acceptance remains tracked separately in `PERF-B007`.
- **Swimming stroke audio cadence** - continuous movement in water now turns the
  existing renderer-independent swim gait contacts into typed
  `PlayerSwimStroke` events, routed to a soft `minecraft:player/swim_stroke`
  default-pack sound separately from enter/exit splash events. Stationary water,
  dry movement, and frames between cadence contacts do not emit strokes. The
  visible `swim-audio-smoke` drove real `W` input through a rendered pool and the
  actual `PygletAudioBackend`: `3.7500` blocks, `2` stroke events, `2` swim
  sounds, one enter plus one exit, and `2` splashes. Metadata:
  `saves/swim_audio_smoke_n1/swim_audio_smoke.json`; visually inspected F2 frame:
  `saves/swim_audio_smoke_n1/screenshots/veilstone_20260711_032204.png`. Full
  gates: import-linter/Ruff/format green, `822 passed`; focused Pyright `0`, full
  baseline unchanged at `389` errors.
- **Visible first-click cold-launch smoke** - `first-click-smoke` opens the real
  visible `GameWindow`, verifies the native Cocoa first-mouse contract, routes
  single clicks through main, Settings, world-list, and pause screens, then
  resumes, rotates the camera, walks through the world, and captures menu plus
  F2 gameplay evidence. All eight frames from the four M2 acceptance runs were
  visually inspected under `saves/first_click_smoke_m2_*`; menu layout remained
  unclipped and gameplay frames showed the loaded world, HUD, crosshair, and no
  stale pointer/pause overlay. Full gates: import-linter/Ruff/format green,
  `810 passed`; focused Pyright `0`, full baseline unchanged at `389` errors.
- **Visible input lifecycle smoke** - `input-lifecycle-smoke` now drives the real
  visible `GameWindow` through walk/release, deliberately missing `W+Shift`
  releases at pause, two single-click Resume cycles, inventory, focus
  deactivate/activate, first-motion camera rotation, and normal F2 capture. It
  writes validated numeric JSON and skips explicitly without a display. Focused
  CLI/input/metadata coverage: `80 passed`; focused Pyright: `0` errors; full
  unit gate: `791 passed`, `10` display-dependent skips. Real metadata and
  visually inspected screenshot:
  `saves/input_lifecycle_smoke_m1/input_lifecycle_smoke.json`,
  `saves/input_lifecycle_smoke_m1/screenshots/veilstone_20260710_065056.png`.
- **Rendered reference gameplay screenshot** - the new
  `reference-gameplay-screenshot` CLI consumes the existing renderer-independent
  fixture, offsets all `160` blocks above a fresh temporary world, applies one
  deterministic isometric camera, rebuilds the affected chunk synchronously,
  and writes validated numeric JSON through a narrow tool module. Real GL
  evidence recorded `1` rebuilt chunk, `6` visible sections, and `52` water
  triangles. The final scene-only screenshot was visually inspected after an
  initial review caught and removed the first-person hand overlay:
  `saves/reference_gameplay_screenshot_l2/screenshots/veilstone_20260710_063329.png`.
  Focused CLI/layout/metadata coverage: `18 passed`; focused Pyright: `0`
  errors; full unit gate: `782 passed`, `10` display-dependent skips.
- **Reproducible inventory interaction smoke** - the new
  `inventory-interaction-smoke` CLI runs selected resource-pack icon,
  crafting-result/input quick-move, right/left drag, and right-click split
  scenarios through the real input/controller path. Each scenario validates a
  stable numeric metadata contract, saves sorted JSON, and captures through
  `GameWindow.save_screenshot()`; display-less runs exit successfully with an
  explicit skip. Unit/parser coverage: `19 passed`; full unit gate: `782`
  passed; focused Pyright: `0` errors. All six real OpenGL captures passed under
  `saves/inventory_interaction_smoke_l1/<scenario>/`, including
  `icons/screenshots/veilstone_20260710_061724.png` and
  `left-drag/screenshots/veilstone_20260710_061508.png`.
- **Capacity-aware left-drag distribution** - left-drag now collects ordered
  distinct inventory/crafting targets in input gesture state, then delegates one
  even allocation to `InventoryLogic`. Incompatible/full targets are skipped,
  duplicate targets are ignored, per-slot max stacks are respected, and all
  unaccepted items remain on the cursor. Real mixed-target smoke:
  `saves/left_drag_distribution_smoke_k6/screenshots/left_drag_mixed_capacity.png`,
  metadata `saves/left_drag_distribution_smoke_k6/left_drag_distribution_smoke.json`
  (`10` carried, `7` accepted across `3` slots, cursor remainder `3`).
- **Right-drag single-item distribution** - right-dragging a carried stack now
  places one item into each distinct inventory or crafting slot crossed by the
  gesture. Source/revisited slots are skipped, incompatible/full slots reuse the
  existing no-op right-click rules, cursor exhaustion stops distribution, and
  button release does not duplicate the last target. Real smoke:
  `saves/right_drag_distribution_smoke_k5/screenshots/right_drag_three_slots.png`,
  metadata `saves/right_drag_distribution_smoke_k5/right_drag_distribution_smoke.json`
  (`6 -> 3 + 1 + 1 + 1`, revisited target remains `1`, cursor empty).
- **Crafting-input quick-move** - Shift-clicking a crafting input now returns
  its stack directly to inventory through `InventoryLogic`: existing stacks are
  merged first, accepted items are removed from the grid, any remainder stays
  in place, and the cursor is untouched. Unit and real-GL integration cover
  full, partial, and rejected transfers. Real smoke:
  `saves/crafting_input_quick_move_smoke_k4/screenshots/shift_click_input.png`,
  metadata
  `saves/crafting_input_quick_move_smoke_k4/crafting_input_quick_move_smoke.json`
  (5 logs moved, input empty, cursor empty, state identity preserved).
- **Transactional crafting-result quick-move** - Shift-clicking a valid result
  now repeatedly crafts directly into inventory while capacity remains. Each
  result is tested against a cloned inventory before ingredients are consumed,
  so full inventory and stack limits cannot lose inputs; ordinary result clicks
  still place one craft on the cursor. Real GL smoke:
  `saves/crafting_quick_move_smoke_k3/screenshots/shift_click_result.png`, with
  metadata `saves/crafting_quick_move_smoke_k3/crafting_quick_move_smoke.json`
  (3 logs -> 12 planks, input empty, cursor empty, state identity preserved).
- **Resource-pack-aware inventory icons** - the icon factory now consumes the
  active renderer atlas instead of creating a procedural default, and a narrow
  presentation adapter applies live pack switches to both world rendering and
  existing hotbar/inventory/crafting/cursor sprites without rebuilding gameplay
  state. Fake-atlas tests lock top/side changes and non-block fallback stability;
  real default/contrast GL captures:
  `saves/inventory_icon_smoke_k2/screenshots/default_inventory.png`,
  `saves/inventory_icon_smoke_k2/screenshots/contrast_pack_inventory.png`, with
  metadata `saves/inventory_icon_smoke_k2/inventory_icon_smoke.json`
  (`grass_changed=true`, controller and inventory identity preserved).
- **Isometric block inventory icons** - block items now reuse
  `ItemModelSnapshot` top/side texture slots in a pure nearest-neighbor PIL
  composer, producing a compact three-face Minecraft-like silhouette across
  inventory, hotbar, crafting, and cursor sprites. Transparent/cutout pixels and
  source pixel colors are preserved; resource and fluid-container fallback
  icons are unchanged. Real inventory GL smoke:
  `saves/inventory_icon_smoke_k1/screenshots/veilstone_20260710_050110.png`
  with metadata `saves/inventory_icon_smoke_k1/inventory_icon_smoke.json`.
- **Detail-gated shoreline water cue** - water meshing now emits a render-only
  shoreline factor for top vertices touching opaque terrain, and the detailed
  water shader turns it into a subtle animated edge tint while `low_60` keeps
  the previous output. The water VAO reuses the existing 15-float stride with an
  explicit shoreline attribute; simulation/source levels are unchanged. Real
  180-frame A/B:
  `saves/water_surface_smoke_j5_final/low_60/screenshots/veilstone_20260710_044309.png`,
  `saves/water_surface_smoke_j5_final/detailed/screenshots/veilstone_20260710_044319.png`,
  metadata `saves/water_surface_smoke_j5_final/water_surface_smoke.json`
  (68 shoreline vertices, 162 water triangles, both `item_y=97.86`,
  `item_vy=-0.0001`, `last_jitter=0.0001`).
- **Reproducible water surface smoke** - new `python -m voxel_sandbox
  water-surface-smoke` builds a deterministic closed pool in a fresh temporary
  world for matched `low_60` and custom `detailed` profiles, captures screenshots,
  and writes JSON with the
  resolved water-detail state, floating-item stability, pending work, and actual
  GPU water mesh sections/triangles. The tool fails if the scene has fluid data
  but no visible water mesh. Real 180-frame capture:
  `saves/water_surface_smoke_j4_clean/water_surface_smoke.json`,
  `saves/water_surface_smoke_j4_clean/low_60/screenshots/veilstone_20260710_043327.png`,
  `saves/water_surface_smoke_j4_clean/detailed/screenshots/veilstone_20260710_043337.png`
  (both `item_y=97.86`, `item_vy=-0.0001`, `last_jitter=0.0001`,
  `water_mesh_triangles=162`).
- **Procedural water ripple reflections** - detailed water profiles now perturb
  the top-surface normal with two low-cost animated ripple fields, making
  Fresnel/sky reflection cues readable from shallow camera angles while
  `low_60` retains the previous base-normal path. Real GL smoke:
  `saves/water_ripple_smoke/screenshots/veilstone_20260710_041105.png`
  (`water_detail=true`, `item_y=87.86`, `item_vy=-0.0001`,
  `last_jitter=0.0`).
- **Water detail quality gating** - render quality profiles now gate extra water
  crest/glint detail: `low_60` keeps the cheaper base water path, while higher
  profiles keep detailed highlights. F3 diagnostics and Settings live preset
  application now show/apply the water detail state. Real quality smoke:
  `saves/water_detail_quality_smoke/low_60/screenshots/veilstone_20260709_161959.png`,
  `saves/water_detail_quality_smoke/high/screenshots/veilstone_20260709_162004.png`
  (`low_60 water_detail=false`, `high water_detail=true`, both
  `last_jitter=0.0003`).
- **Water surface crest highlights** - water shader now layers low-cost moving
  crest/glint highlights over the existing animated water texture/fresnel path,
  making pools read more like water while leaving fluid simulation untouched.
  Real water smoke:
  `saves/water_surface_smoke_visible/screenshots/veilstone_20260709_160354.png`
  (`item_y=88.8599`, `item_vy=0.0002`, `last_jitter=0.0003`).
- **Shadow preset smoke captures** - `python -m voxel_sandbox
  shadow-preset-smoke` now captures `off`/`low`/`medium`/`high_material_preview`
  screenshots plus JSON metadata for comparing shadow artifacts across quality
  settings. Real smoke evidence:
  `saves/shadow_preset_smoke/shadow_preset_smoke.json`,
  `saves/shadow_preset_smoke/off/screenshots/veilstone_20260709_153135.png`,
  `saves/shadow_preset_smoke/medium/screenshots/veilstone_20260709_153138.png`,
  `saves/shadow_preset_smoke/high_material_preview/screenshots/veilstone_20260709_153139.png`.
- **Quality preset Settings UI** - Settings now has a `Quality Preset` item
  cycling `custom`/`low_60`/`balanced`/`high`/`cinematic`; selecting a preset
  live-applies material quality, fog, clouds, and vegetation wind while status
  text calls out restart-bound shadows/smooth lighting/AO/render-distance
  effects. Long Settings menus now compact their button layout so the preset row
  no longer overlaps the title. Real settings smoke screenshots:
  `saves/settings_preset_smoke_visible/screenshots/veilstone_20260709_150104.png`,
  `saves/settings_preset_smoke_visible/screenshots/veilstone_20260709_150106.png`.
- **Quality preset F3 diagnostics** - F3 debug text now includes the active
  quality preset plus resolved shadow/cloud/wind state next to existing
  smooth/AO/fog/material diagnostics. Real F3 material-preview smoke screenshot:
  `saves/f3_preset_smoke/screenshots/veilstone_20260709_151033.png`.
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
- **Material visual snapshots** - block model snapshots now expose render-facing
  material visuals with color atlas rects, tint, and optional normal/specular
  rects, preparing shader quality variants without binding extra textures in
  the default color-only runtime.
- **Material visual lookup consumer** - chunk mesh visual lookups now consume
  `MaterialVisualSnapshot` data and can build optional normal/specular rect
  arrays for opt-in material profiles while existing color-only mesh paths keep
  their unchanged call sites.
- **Material shader variant scaffold** - render material quality decisions now
  resolve explicit chunk shader variants so `color-only` and `low` stay on
  `chunk_opaque`, while `material-preview` names a future opt-in material shader
  path that requires material atlases.
- **Material atlas binding plans** - render code now has a pure material atlas
  binding plan helper that returns no bindings for `color-only` and `low`, while
  `material-preview` deterministically names sampler uniforms and texture units
  only for available material atlas roles.
- **Material shader setup fixture** - render code now assembles shader variant and
  material atlas binding setup together, proving default/low profiles skip
  material shader work while `material-preview` consumes the opt-in binding plan.
- **Opt-in material runtime hook** - `WorldScene` now builds a
  `MaterialShaderSetup` planning hook and only loads CPU material atlas bundles
  when the material pipeline requests them, keeping default profiles on the
  existing color-only shader path.
- **Material shader runtime wiring plan** - render code now names future
  material-preview shader files and planned material bindings without replacing
  the default `chunk_opaque` `ShaderProgram` startup path.
- **Material-preview shader fixture** - added opt-in `chunk_material_preview`
  shader fixture files matching the existing chunk mesh attribute contract and
  planned material sampler names while default startup still loads `chunk_opaque`.
- **Guarded material shader activation** - added a render-side activation helper
  that skips default profiles and compiles the material-preview shader fixture
  with only the planned material bindings when explicitly requested.
- **Opt-in material shader WorldScene hook** - `WorldScene` now stores and
  releases a guarded material shader activation only when the material-preview
  setup requests it, leaving default profiles on the existing chunk shader path.
- **Opt-in material sampler binding application** - material shader runtime code
  can now apply planned sampler texture units only to an activated material
  shader, leaving default/low profiles with no sampler writes.
- **Opt-in material atlas GL texture helper** - render code can now create
  configured GL textures only for material atlas roles requested by active
  bindings, omitting missing roles without placeholder textures.
- **Opt-in material atlas texture WorldScene hook** - `WorldScene` now creates
  and releases material atlas GL textures only when a material shader activation
  and material bundle exist, keeping default/low profiles with an empty material
  texture map and no placeholder textures. Real gameplay smoke screenshot:
  `saves/screenshots/veilstone_20260709_034632.png`.
- **Quality preset renderer wiring** - `GameWindow` now resolves
  `graphics.quality_preset` into a `RenderQualityProfile` and constructs the
  world renderer from its knobs (shadows, smooth lighting, AO, fog, material
  quality, vegetation wind, optional render-distance override); `custom` keeps
  the existing per-flag path unchanged. Real preset smokes: `low_60`
  `saves/screenshots/veilstone_20260709_045009.png` (Smooth False, AO False,
  no shadows, color-only), `high`
  `saves/screenshots/veilstone_20260709_045011.png` (shadows + smooth +
  `material-preview bundle on`).
- **Render quality preset resolution** - added render-facing
  `RenderQualityProfile` with `low_60`/`balanced`/`high`/`cinematic` presets and
  a persisted `graphics.quality_preset` setting (default `custom` keeps
  existing individual flags, zero behavior change). Default gameplay smoke
  unchanged: `saves/screenshots/veilstone_20260709_044535.png`.
- **Material-preview lighting balance** - added `u_material_has_<role>` flag
  uniforms so absent material roles no longer alias texture unit 0 (unbound
  emissive/MER samplers were re-adding the color atlas as fake emissive light,
  washing out the preview), and replaced the flat normal-z boost with a
  zero-mean tangent detail term. Preview brightness now matches the default
  profile with per-pixel normal detail only. Screenshots: preview
  `saves/screenshots/veilstone_20260709_043947.png` vs default
  `saves/screenshots/veilstone_20260709_043950.png`.
- **Specular sidecar content** - the sidecar generator now also produces
  brightness-scaled `_s.png` specular maps for stone and diamond ore, so the
  material-preview profile binds both NORMAL and SPECULAR atlas roles. Real
  material-preview smoke: `saves/screenshots/veilstone_20260709_043336.png`.
- **Settings UI materials toggle** - the Settings screen now has a
  `Materials: <quality>` item cycling color-only/material-preview through
  `ApplyMaterialQualityUseCase` with live renderer hot-swap and persisted
  settings. Real in-app menu smoke: settings screen with applied status
  `saves/screenshots/veilstone_20260709_043059.png`, gameplay after toggle
  `saves/screenshots/veilstone_20260709_043100.png` (`material-preview bundle
  on`).
- **Material sidecar generator + terrain normal maps** - added
  `scripts/generate_material_sidecars.py` producing deterministic height-based
  `_n.png` normal sidecars, and shipped them for ten core terrain/wood blocks
  in the default pack (stone, dirt, grass, oak, diamond ore, crafting table).
  Real material-preview smoke with the full sidecar set:
  `saves/screenshots/veilstone_20260709_042246.png`.
- **/materials command for material quality** - new `/materials
  <color-only|low|material-preview>` command routes through
  `ApplyMaterialQualityUseCase` (settings persist + renderer hot-swap), and
  `WorldScene.apply_material_quality` rebuilds the material pipeline, chunk
  shader, and mesh cache in the running game. Real in-app toggle smoke:
  default→preview→default screenshots
  `saves/screenshots/veilstone_20260709_041858.png`,
  `saves/screenshots/veilstone_20260709_041900.png` (preview shading + status
  line), `saves/screenshots/veilstone_20260709_041902.png` (default restored).
- **Material-preview chunk draw path** - when the material-preview activation
  exists, `WorldScene` now draws chunks with the activated
  `chunk_material_preview` shader (releasing the unused default program), while
  default/low profiles keep the exact `chunk_opaque` path. Real checks:
  material-preview smoke shows per-pixel normal-mapped stone shading
  `saves/screenshots/veilstone_20260709_040826.png`, default gameplay smoke
  unchanged `saves/screenshots/veilstone_20260709_040852.png`.
- **Stone normal sidecar in default pack** - the bundled default resource pack
  now ships a deterministic `stone_n.png` normal-map sidecar, the bundled-pack
  atlas path discovers material manifests, and material binding plans start at
  texture unit 2 so material atlases never clobber the shadow map (fixes
  `BUG-R003`). Real checks: material-preview smoke with NORMAL role
  `saves/screenshots/veilstone_20260709_040210.png` (sun-lit shading matches
  default), default gameplay smoke unchanged
  `saves/screenshots/veilstone_20260709_035810.png`.
- **Material-preview end-to-end real-scene verification** - ran the hidden-window
  gameplay smoke with `material_quality = "material-preview"` against a real GL
  context: activation, atlas texture creation, and sampler binds work without
  crashes and default output stays unchanged. Screenshots: material-preview
  `saves/screenshots/veilstone_20260709_035136.png` (overlay
  `material-preview bundle on`), default baseline
  `saves/screenshots/veilstone_20260709_035011.png`.
- **Opt-in material sampler/texture bind WorldScene hook** - `WorldScene` now
  applies planned material sampler texture units once at setup and binds created
  material atlas textures each frame in the chunk draw path, staying a no-op for
  default/low profiles with an empty material texture map. Real gameplay smoke
  screenshot: `saves/screenshots/veilstone_20260709_035011.png`.
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

- **Zero-source light propagation fast path** - relight now returns an
  independent zero `uint8` volume before allocating propagation scratch arrays
  when a region has no skylight or block-light source. Deterministic coverage
  preserves input ownership, opaque volumes, lantern/removal, randomized, and
  cross-chunk behavior. On a 128x48x48 volume, the zero-source path measured
  `0.0107 ms` versus `0.3277 ms` for a one-source propagation (`30.5x`); the
  complete workload remained update-bound at RD3 p95 `11.020 ms` and RD4 p95
  `13.655 ms`, so this is retained as a narrow win rather than treated as the
  full 60 FPS solution. A visible 2560x1440 F3/F2 pass removed the targeted
  lantern through the normal left-click path, spawned its item drop, and
  correctly cleared surrounding light with no stale bright voxels. Inspected
  frames:
  `saves/lighting_zero_n12/screenshots/veilstone_20260720_095210.png` and
  `saves/lighting_zero_n12/screenshots/veilstone_20260720_095212.png`.
- **Lighting propagation scratch-buffer reuse** - the measured NumPy hotspot now
  reuses per-call attenuated/neighbor/update arrays and in-place ufunc outputs
  across its bounded 15 propagation steps instead of allocating fresh volumes
  each iteration. Existing opaque/emissive/removal/cross-chunk behavior plus 12
  deterministic randomized volumes match the former implementation byte for
  byte; full unit passed `844`, focused Pyright passed with `0`, and the full
  baseline stayed `389`. On a 3x3x128 volume, skylight median improved
  `11.800 -> 10.746 ms` (`-8.9%`); RD3 p95 improved `11.164 -> 9.791 ms`, RD4
  `15.236 -> 13.270 ms`, and RD4 max `19.004 -> 17.570 ms`. Reprofiling reduced
  `_propagate_light` self time `554.908 -> 500.645 ms`. A visible RD4/F3 pass
  loaded `81` chunks with `Pending 0`; skylight/shadows were inspected in F2:
  `saves/lighting_scratch_n11/screenshots/veilstone_20260711_045031.png`.
- **RD4 update-stage profile attribution** - `benchmark-frame-streaming` now has
  an opt-in `--profile-update` mode that profiles only measured `fixed_update`
  calls after warmup and prints a stable, bounded, Veilstone-only cumulative/self
  time table; normal output is unchanged without the flag. Pure formatter/filter
  coverage and CLI tests passed (`18` focused), full unit passed `842`, focused
  Pyright passed with `0`, and the full baseline stayed `389`. The unprofiled RD4
  control remained update-bound in `60/60` frames. The 240-frame RD4 profile was
  update-bound in `240/240`: `relight_chunks` led at `659.149 ms` cumulative and
  `_propagate_light` at `554.908 ms` self across `462` calls, well ahead of queue
  selection (`269.128 ms` cumulative). This selects only lighting propagation
  scratch-buffer churn for N11 rather than speculative meshing/render changes.
- **Streaming bottleneck distribution** - the shared public frame classifier now
  drives both F3 and `benchmark-frame-streaming`, whose stable summary reports
  update/render/balanced/idle frame counts without importing Pyglet during pure
  formatting tests. Focused tests passed `7`, full unit passed `840`, focused
  Pyright passed with `0`, and the full baseline stayed at `389`. RD3 measured
  p95 `11.164 ms` (max `13.536`) with `update:238`, `render:2`; RD4 measured p95
  `15.236 ms` (max `19.004`) with `update:240`, `render:0`. RD4 update p95 was
  `14.485 ms` versus render p95 `0.756 ms`, establishing update-path attribution
  as the next performance step rather than speculative render work.
- **Coarse frame bottleneck indicator** - `RuntimePerfTracker` now derives an
  immutable `idle`/`balanced`/`update`/`render` label from the update/render
  timings it already owns, and F3 shows the result on the existing timing line
  without adding new timers or renderer/controller reads. Pure tests cover all
  four semantics and HUD formatting: `9` focused tests passed, full unit passed
  `838`, focused Pyright passed with `0`, and the full known-red baseline stayed
  `389`. A direct visible `rtk uv` run showed `Update 1.2`, `Render 5.3`, and
  `Bottleneck render`; the complete F3/world frame was inspected at
  `saves/frame_bottleneck_n8/screenshots/veilstone_20260711_043126.png`.
- **Relight queue diagnostics** - the existing immutable render queue snapshot
  now exposes pending bounded relight work, `DemoWorldRenderer` populates it at
  the renderer-to-HUD boundary, and F3 displays `Stream relight` beside mesh and
  remesh queues without reaching into renderer internals. Snapshot defaults,
  renderer aggregation, and HUD formatting are covered by `10` focused tests;
  full unit passed `836`, focused Pyright passed with `0`, and the full known-red
  baseline remained `389`. A direct visible `rtk uv` run toggled F3 through the
  normal key path, displayed `Stream relight 3`, and saved through F2; the full
  world/HUD frame was visually inspected at
  `saves/relight_diagnostics_n7/screenshots/veilstone_20260711_042757.png`.
- **Collision-critical streaming queue priority** - player physics now owns a
  deterministic ordered collision-chunk footprint, and synchronous collision
  loading reuses the same negative/boundary-safe coordinate rule. `GameWindow`
  passes only the resulting chunk set into streaming; at equal camera distance,
  collision-critical relight/remesh work wins before visible work, while nearer
  work, budgets, FIFO ties, and unavailable-data fallback retain their previous
  behavior. Focused coverage passed `30` tests; full unit passed `834`; full
  Pyright stayed at the known `389`-error baseline. Benchmarks: RD3 p95
  `11.375 ms` (max `13.762`), RD4 p95 `12.651 ms` (one max spike `33.111`). In
  the visible RD4 pass, a real `W` press moved the player from `x=15.75` to
  `x=18.08` across the `x=16` chunk boundary in 28 frames; the recorded footprint
  contained chunks `(0,0)` and `(1,0)` together at the boundary, F3 remained
  active, and the inspected F2 frame is
  `saves/collision_priority_n6/screenshots/veilstone_20260711_042337.png`.
- **Camera-visible streaming queue priority** - `WorldScene` now retains its
  latest real render frustum as a renderer-owned visibility snapshot. At equal
  camera distance, visible relight/remesh work drains before off-screen work;
  nearer work still wins first, FIFO ties remain stable, and pre-first-render
  `None` preserves the previous deterministic fallback. Pure AABB/order tests
  plus a world-scene integration test cover the policy. Benchmarks: RD3 p95
  `11.232 ms` (max `12.533`), RD4 p95 `12.229 ms` (one max spike `23.808`),
  mesh queue `3` in both. The visible RD4 pass rotated `180°`, refreshed the
  frustum, walked `10.0` blocks, and reached `81` loaded chunks with `Pending 0`;
  inspected F2:
  `saves/stream_visibility_n5/screenshots/veilstone_20260711_041407.png`. Full
  gates: `830 passed`, focused Pyright `0`, full baseline `389`.
- **Camera-distance streaming queue priority** - bounded relight and remesh
  queues now drain nearer chunks before farther chunks while preserving FIFO
  insertion order for equal distances and leaving unselected queue order intact.
  Negative coordinates and zero budgets are covered by pure scheduling tests.
  RD3 frame-streaming stayed below budget at p95 `9.778 ms` (max `14.368 ms`),
  with `43` loaded chunks, `4` pending chunks, and mesh queue `2`. A visible RD3
  walking/F3 pass reached `49` loaded chunks with `Pending 0`; inspected F2:
  `saves/stream_priority_n4/screenshots/veilstone_20260711_033532.png`. Full
  gates: `825 passed`, focused Pyright `0`, full baseline `389`.
- **Backlog truth audit** - removed 7 rendering entries already marked
  `fixed`/`done` and represented in current code/CHANGELOG. The 15 remaining
  entries are all genuinely `open`; partially implemented architecture,
  landmark/event, diagnostics, streaming, and low-end performance items now
  describe only their unimplemented remainder instead of inviting completed
  snapshots, event/audio routing, quality tiers, water, or FIFO budgets to be
  rebuilt.
- **Backlog promotion and real-game acceptance rules** - agent guidance now
  requires active tasks to move from `BACKLOG` into `WORKPLAN` without
  duplication, then move completed results into `CHANGELOG`. Player-facing
  acceptance now requires a visible-game interaction pass, normal screenshots,
  and actual visual inspection; controls work additionally checks key release,
  first-click behavior, pause/Resume, mouse recapture, and first-motion camera
  response. The newly reported stuck-key, initial double-click, and Resume
  capture regressions are tracked separately in `docs/BUGS.md`.
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
