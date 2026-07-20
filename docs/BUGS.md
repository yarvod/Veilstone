# Known Bugs & Issues

This file tracks active bugs, regressions, flaky tests, and unresolved quality issues. Completed historical fixes belong in `docs/CHANGELOG.md`.

## Open

### BUG-R008: Dusk Highlands form abrupt walls and pillar forests

- **Status:** fixed
- **Affected area:** world generation / biome blending / highland features
- **Observed:** fresh deterministic benchmark worlds can produce a flat stone
  wall at the Dusk Highlands boundary plus many isolated one-block-wide stone
  columns capped with ore. The result reads as broken chunk geometry even though
  repeated captures prove the meshes are complete.
- **Cause:** biome selection applies the highlands `base_height = 80` immediately
  beside plains `base_height = 64` without transition blending, while the
  highland decorator accepts roughly 4% of individual x/z columns as pillars.
- **Evidence:** visually inspected standalone CGL captures
  `saves/perf_rd12_n15/rd12_low60_long_walk.png` and
  `saves/perf_rd12_n15/rd12_low60_batched.png`; the final woods capture
  `saves/perf_rd12_n15/rd12_low60_acceptance_nice.png` confirms fog culling and
  streaming do not create equivalent missing geometry.
- **Expected:** biome elevation transitions produce readable ridges/slopes, and
  highland landmarks form sparse coherent clusters instead of a dense field of
  isolated vertical needles.
- **Fix notes:** registry-driven terrain now blends biome base height and hill
  variation through continuous temperature/moisture weights. Highlands features
  are deterministic 16x16-cell candidates with circular stepped bases, bounded
  density, one ore crown, and identical placement across chunk boundaries.
- **Verification:** boundary regression coverage sampled at least 100 discrete
  biome transitions and caps adjacent height delta at two blocks. The inspected
  1800-frame RD12 scene replaces the former wall with a terraced ridge:
  `saves/terrain_n16/rd12_1800_highlands.png`; close highland evidence is
  `saves/terrain_n16/highland_formations.png`. Visible `GameWindow` input/F2
  acceptance passed at
  `saves/terrain_n16/visible_game/screenshots/veilstone_20260720_145054.png`.

### BUG-R007: Selection highlight shows translucent diagonal bands

- **Status:** open
- **Affected area:** render / block selection highlight / transparency
- **Observed:** the selected block face can contain overlapping translucent
  diagonal/triangular bands instead of one uniform subtle highlight; nearby
  natural skylight and terrain shadows remain coherent, so this is visually
  distinct from the fixed broad terrain-shadow artifact in `BUG-R006`.
- **Reproduction:** enter a visible world, aim at a nearby stone block with the
  default color-only material profile, and inspect the filled selection overlay.
  Current F2 evidence:
  `saves/lighting_scratch_n11/screenshots/veilstone_20260711_045031.png`.
- **Expected:** the yellow outline remains readable and each selected face has a
  uniform low-alpha fill without internal diagonal bands or stacked-face
  overdraw.

### BUG-I001: Movement keys can remain active after release

- **Status:** fixed
- **Affected area:** input / movement / focus and key-state lifecycle
- **Observed:** during real gameplay the player can occasionally continue
  moving or running after the movement key is no longer held.
- **Reproduction:** intermittent user report; enter a world, move and sprint with
  normal keyboard input, release the movement keys, and repeat around focus,
  inventory, and pause transitions until movement remains active.
- **Expected:** releasing a movement key, losing focus, opening inventory, or
  entering the pause menu clears the corresponding gameplay key state
  immediately.
- **Fix notes:** entering pause through Escape now clears `KeyState` before the
  menu transition, matching inventory, text-input, and deactivate boundaries.
  This prevents a missed OS key-release event from becoming active again after
  Resume.
- **Verification:** the visible `input-lifecycle-smoke` deliberately holds
  `W+Shift` while entering pause without sending release events, resumes twice
  by single click, and exercises inventory plus deactivate/activate. It measured
  `walk_distance=0.1667`, ordinary and post-Resume drift `0.0000`, and confirmed
  pause/inventory/focus clears plus mouse recapture. Metadata:
  `saves/input_lifecycle_smoke_m1/input_lifecycle_smoke.json`; visually inspected
  F2 frame:
  `saves/input_lifecycle_smoke_m1/screenshots/veilstone_20260710_065056.png`.

### BUG-I002: Fresh game UI can require double clicks

- **Status:** fixed
- **Affected area:** input / menu UI / initial mouse focus and event routing
- **Observed:** on some launches, if the mouse is not moved or focused in the
  expected way, menu buttons and other interactions respond only to a double
  click instead of the first single click.
- **Reproduction:** intermittent user report; launch the visible client fresh,
  vary initial mouse movement/focus before interacting, then try each initial
  menu action with one click.
- **Expected:** the first ordinary click activates the intended UI control
  regardless of the initial mouse movement pattern.
- **Fix notes:** on macOS, the Pyglet Cocoa view now implements
  `acceptsFirstMouse:` before window construction, so the activating click is
  delivered to the existing press/release widget path instead of being consumed
  by AppKit. Other platforms are unchanged; no debounce or duplicate dispatch
  workaround was added.
- **Verification:** four independent visible cold launches (two without initial
  pointer motion and two with it) reported `cocoa_accepts_first_mouse=True`,
  exact Settings/Back/Singleplayer/Cancel/Resume callback counts
  `1,1,1,1,1`, immediate Resume capture, `2.8800` degrees of first-motion yaw,
  and nonzero player movement. Metadata and all visually inspected menu/game
  frames live under `saves/first_click_smoke_m2_no_motion/`,
  `saves/first_click_smoke_m2_no_motion_2/`,
  `saves/first_click_smoke_m2_motion_1/`, and
  `saves/first_click_smoke_m2_motion_2/`.

### BUG-I003: Resume leaves mouse visible and camera uncaptured

- **Status:** fixed
- **Affected area:** input / pause menu / exclusive mouse capture
- **Observed:** after pressing Escape during gameplay and clicking `Resume`, the
  pointer can remain visible and mouse movement no longer rotates the camera
  correctly.
- **Reproduction:** enter a world, confirm normal camera control, press Escape,
  click `Resume`, then move the mouse without any extra click.
- **Expected:** Resume immediately hides/recaptures the pointer, returns input to
  gameplay, and rotates the camera on the first mouse movement.
- **Verification required:** test repeated Escape/Resume cycles through the
  visible client and verify both the internal capture state and real first-motion
  camera behavior; existing mocked sync-call coverage is not sufficient.
- **Fix notes:** the mouse menu callback now detects target-screen transitions
  and synchronizes both game state and exclusive mouse capture, matching the
  keyboard menu path. A focused callback regression test covers the missing
  synchronization. After-fix visible verification confirmed one-click Resume,
  `mouse_captured=true`, and `1.44` degrees of camera yaw on the first motion;
  F2 evidence:
  `saves/visible_gameplay_l2/screenshots/veilstone_20260710_064333.png`.

### BUG-T001: test_ui_renderer fails when run after other render tests

- **Status:** fixed
- **Affected area:** tests / pyglet UI renderer test isolation
- **Observed:** `uv run pytest tests/unit/render` currently fails all 9
  `test_ui_renderer.py` cases with
  `pyglet.gl.current_context.create_program` reading a `None` context, while the
  same file passes in isolation and the `-m unit` gate stays green. Reverified
  before Phase N2 promotion; this is shared Pyglet/GL test state, not a widget
  layout/callback failure.
- **Reproduction:** `uv run pytest tests/unit/render` (fails) vs
  `uv run pytest tests/unit/render/test_ui_renderer.py` (passes).
- **Fix notes:** the capability probe still closes its temporary window, but the
  UI renderer module now owns a separate hidden shader-capable window for the
  full module fixture lifetime. This keeps a valid current context even when the
  preceding HUD snapshot module disables Pyglet's shadow window; production UI
  code and display-less skip behavior are unchanged.
- **Verification:** the shortest reproducer
  (`test_hud_debug_snapshot.py` then `test_ui_renderer.py`) passes `13` tests;
  `tests/unit/render` passes all `122`; full unit gate passes `822` with no new
  skips. Focused Pyright is clean and the full baseline remains `389` errors.

### BUG-R006: Shadow artifacts on terrain surfaces

- **Status:** fixed
- **Affected area:** render / shadows / material-preview lighting
- **Observed:** user screenshots and F3 material-preview smoke
  `saves/f3_preset_smoke/screenshots/veilstone_20260709_151033.png` show hard
  triangular/blocky dark shadow artifacts across terrain and cave/stone surfaces.
- **Reproduction:** `uv run python -m voxel_sandbox shadow-preset-smoke --frames
  40 --render-distance 2 --output-dir saves/shadow_preset_smoke` captures
  preset metadata in `saves/shadow_preset_smoke/shadow_preset_smoke.json`.
  `off` screenshot is clean, while `medium` and `high_material_preview`
  reproduce the broad triangular dark receiver artifacts:
  `saves/shadow_preset_smoke/medium/screenshots/veilstone_20260709_153138.png`,
  `saves/shadow_preset_smoke/high_material_preview/screenshots/veilstone_20260709_153139.png`.
- **Fix notes:** chunk shadow receivers now use a wider 5x5 PCF average and a
  softer shadow floor (`0.48`) in both color-only and material-preview shaders,
  removing the single-center-sample hard clamp that made projected terrain
  edges read as black triangular artifacts. After-fix smoke:
  `saves/shadow_preset_smoke_after_fix/medium/screenshots/veilstone_20260709_155439.png`,
  `saves/shadow_preset_smoke_after_fix/high_material_preview/screenshots/veilstone_20260709_155441.png`.

### BUG-G008: Dropped items jitter in water instead of floating

- **Status:** fixed
- **Affected area:** gameplay physics / item drops / fluids
- **Observed:** user reports item drops in water tremble/jitter; expected
  behavior is buoyant rise toward the water surface and stable bobbing/float.
- **Fix notes:** item/mob vertical physics now targets the detected nearby fluid
  surface and damps toward it instead of applying constant upward velocity until
  leaving water. Unit coverage locks stable item-in-water buoyancy; real smoke
  `saves/item_water_smoke/screenshots/veilstone_20260709_152329.png` measured
  `item_vy=-0.002` and `last_jitter=0.0007`.
- **Regression check:** reusable `water-surface-smoke --frames 180` kept the
  floating item stable in matched `low_60` and `detailed` captures at
  `item_y=97.86`,
  `item_vy=-0.0001`, `last_jitter=0.0001`, with one visible water section, 162
  triangles, and 68 shoreline vertices. Metadata:
  `saves/water_surface_smoke_j5_final/water_surface_smoke.json`.


### BUG-R003: Material atlas bindings clobbered the shadow map texture unit

- **Status:** fixed
- **Affected area:** render / material binding plan / shadow map sampling
- **Observed:** with `material_quality = "material-preview"` and a real material
  atlas role present (stone normal sidecar), sun-lit areas disappeared: the
  material NORMAL atlas was bound to texture unit 1, clobbering the shadow map
  each frame. Deterministically reproduced via material-preview hidden-window
  smoke (`saves/screenshots/veilstone_20260709_035727.png`).
- **Fix notes:** material binding plans now start at texture unit 2, reserving
  unit 0 (color atlas) and unit 1 (shadow map) for the chunk pipeline; unit
  test locks default plan units, and the material-preview smoke restored the
  sun-lit patch to match the default profile.

### BUG-R005: Material toggle could be overwritten by active quality preset

- **Status:** fixed
- **Affected area:** application settings / render quality presets
- **Observed:** explicit `/materials` or Settings material quality changes were
  saved to `graphics.material_quality`, but a non-custom `quality_preset` could
  resolve back to its preset material quality on the next renderer rebuild or
  restart.
- **Fix notes:** `ApplyMaterialQualityUseCase` now sets `quality_preset =
  "custom"` when applying an explicit material override, preserving the user's
  direct material choice.

### BUG-R004: No-shadow quality preset leaves shadow sampler unbound

- **Status:** fixed
- **Affected area:** render / quality presets / shadow sampling
- **Observed:** `quality_preset = "low_60"` disabled shadow map creation but chunk
  shaders still exposed `sampler2DShadow shadow_map` on texture unit 1; macOS
  Metal warned about an unloadable/wrong sampler binding during real gameplay
  smoke.
- **Fix notes:** `WorldScene` now owns a neutral 1x1 cleared depth texture and
  binds it whenever real shadows are disabled; `low_60` gameplay smoke now runs
  without the sampler warning.

### BUG-R002: Water mesh VAO required vegetation wind attribute

- **Status:** fixed
- **Affected area:** render / water mesh upload / shader attributes
- **Observed:** real game startup/render could crash in ModernGL VAO creation with
  `KeyError: 'in_wind_motion'` when water meshes were uploaded, because the
  water shader does not declare the vegetation-only wind attribute.
- **Fix notes:** water `SectionMeshCache` instances now bind 15-float transparent
  water mesh layouts and skip `in_wind_motion` for visible and depth VAOs;
  focused unit coverage locks the no-wind water cache path. Real gameplay smoke
  uploaded water meshes, moved the player, and captured
  `saves/screenshots/veilstone_20260709_014932.png`.

### BUG-R001: Packaged app missed data registries

- **Status:** fixed
- **Affected area:** release packaging / packaged smoke startup
- **Observed:** macOS `.app` passed `--version` and the old package verifier, then
  failed on real startup with missing `Contents/Frameworks/data/items.toml`.
- **Fix notes:** release packaging now includes root `data/`, and package
  verification checks item, block, biome, and resource-pack mapping registries
  before running the packaged smoke startup.

### BUG-G001: Player cannot reliably leave water onto shore

- **Status:** fixed
- **Affected area:** player physics / water collision
- **Observed:** player can swim upward, but transitioning from water onto nearby
  land is unreliable or blocked.
- **Fix notes:** player physics now attempts a bounded step-up when horizontal
  movement collides while swimming, with a regression test for swimming onto a
  one-block shore.

### BUG-G002: Water flow surface looks interrupted after block breaks

- **Status:** fixed
- **Affected area:** fluid simulation / water rendering
- **Observed:** flowing water after removing blocks can look visually broken or
  choppy instead of forming a smooth Minecraft-like continuous flow surface.
- **Fix notes:** water mesh generation now smooths top surface vertices across
  neighboring fluid levels using render-side geometry only; voxel water source,
  level, and chunk-boundary rules remain unchanged.

### BUG-G003: Footstep audio and movement presentation are not unified

- **Status:** fixed
- **Affected area:** player feel / audio / animation
- **Observed:** walking camera bob, footstep sounds, player body, and future hand
  animation do not share one gait phase. Footsteps were also too loud by default.
- **Fix notes:** default footstep and block-step gains were lowered, harsh step
  WAVs were regenerated softer; footstep timing now comes from application-layer
  player gait state instead of a separate render-window accumulator.
- **Next action:** extend the existing gait/animation state so bob, sound, body,
  and viewmodel share one polished cadence.

### BUG-G004: Mob walk animations slide and do not match locomotion

- **Status:** fixed
- **Affected area:** entity animation / mobs
- **Observed:** cow and zombie walk loops did not convincingly match leg
  placement, speed, turning, or step contact.
- **Fix notes:** locomotion animation phase now advances from actual grounded
  horizontal velocity, resets while idle/blocked, drives distinct
  idle/walk/attack/hurt/death poses, and exposes footstep contact from the same
  phase used by rendering. Real-game smoke screenshot:
  `saves/screenshots/veilstone_20260630_163807.png`.

### BUG-G005: Leaf/resource-pack transparency not rendered cutout

- **Status:** fixed
- **Affected area:** texture packs / block rendering
- **Observed:** textures with transparent regions, including Faithful-style
  leaves, did not show the world through holes like Minecraft leaves.
- **Fix notes:** cutout blocks now discard transparent atlas texels, leaves are
  non-opaque/cutout in block data, skylight and face culling treat leaves as
  non-occluders, Faithful oak-leaf alpha is preserved through atlas import, and
  a dedicated foliage smoke scene exercises leaves in front of an opaque
  backdrop through the real draw path when an OpenGL display is available.

- **Fix notes:** texture-pack discovery now exposes a single canonical
  `Default` entry, local Java-style packs such as Faithful are not mislabeled
  legacy, and hot-swapping packs preserves chunk shadow-depth meshes.

### BUG-G006: Inventory UI is functional but not Minecraft-polished

- **Status:** open
- **Affected area:** UI / inventory / item rendering
- **Observed:** block icons now have isometric depth and follow the active
  resource pack, but full Minecraft-like crafting interaction polish remains.
- **Fix notes:** stack counts, hover names, drag-and-drop movement, and selected
  and drag slot states are present; inventory UI logic now refreshes the active
  world inventory reference after creating or switching worlds so stale saved
  items cannot leak into the new-world UI state.
- **Fix notes:** block items now use isometric top/side projections from the
  shared `ItemModelSnapshot`; resource/fluid-container fallbacks are unchanged.
  Real GL screenshot:
  `saves/inventory_icon_smoke_k1/screenshots/veilstone_20260710_050110.png`.
- **Fix notes:** inventory/hotbar/crafting/cursor block icons now consume the
  active renderer atlas and refresh in place after live resource-pack switches;
  resource/fluid-container fallbacks and inventory/controller identity are
  preserved. Real A/B screenshots:
  `saves/inventory_icon_smoke_k2/screenshots/default_inventory.png`,
  `saves/inventory_icon_smoke_k2/screenshots/contrast_pack_inventory.png`.
- **Fix notes:** Shift-clicking a crafting result now transactionally repeats the
  recipe into inventory until inputs or capacity run out; rejected output never
  consumes ingredients. Real GL screenshot:
  `saves/crafting_quick_move_smoke_k3/screenshots/shift_click_result.png`.
- **Fix notes:** Shift-clicking a crafting input now merges its stack back into
  inventory, preserves any capacity-limited remainder in the grid, and leaves
  the cursor unchanged. Real GL screenshot:
  `saves/crafting_input_quick_move_smoke_k4/screenshots/shift_click_input.png`.
- **Fix notes:** right-drag now distributes one carried item per distinct
  compatible inventory/crafting slot, skips revisits, and stops when the cursor
  empties. Real GL screenshot:
  `saves/right_drag_distribution_smoke_k5/screenshots/right_drag_three_slots.png`.
- **Fix notes:** left-drag now evenly allocates a carried stack across distinct
  compatible inventory/crafting targets, respects capacity, and keeps remainder
  on the cursor. Real GL screenshot:
  `saves/left_drag_distribution_smoke_k6/screenshots/left_drag_mixed_capacity.png`.
- **Observed:** the K6 smoke showed that derived `No matching recipe` feedback
  immediately masks a fresh `Distributed ...` action message in the inventory
  panel even though `inventory_status` contains the correct result.
- **Fix notes:** a pure resolver now keeps fresh explicit action feedback above
  derived recipe warnings; ordinary clicks clear stale action text. Real GL
  screenshot:
  `saves/inventory_feedback_smoke_k7/screenshots/distribution_action_visible.png`.
- **Observed:** inventory Shift-click currently loops through `Inventory.move()`;
  because `move()` swaps incompatible stacks, an occupied first destination can
  replace the source item and route the wrong stack instead of being skipped.
- **Fix notes:** inventory Shift-click now uses dedicated merge-then-empty
  routing, skips incompatible targets, and preserves the original source
  remainder when destination capacity is exhausted. The new GL test could not
  rerun because the environment reported `screens=0` and no headless `EGL`;
  focused routing/input tests and the full unit gate passed.
- **Observed:** `Inventory.split()` takes `count // 2`, so right-clicking an odd
  inventory stack takes the smaller half, unlike crafting-grid right-click and
  Minecraft ceil-half behavior.
- **Fix notes:** odd inventory splits now take the ceil-half and match crafting;
  even and single-item behavior stayed unchanged in this slice. Focused tests
  passed; the GL case is present but skipped with `screens=0`.
- **Observed:** right-clicking a single inventory item remains a no-op because
  `Inventory.split()` returns `None`, while crafting-grid right-click correctly
  moves the single item to the cursor.
- **Fix notes:** single-item inventory right-click now moves the item to the
  cursor and clears the source, matching crafting; empty, odd/even, placement,
  and drag behavior remain covered. The GL case is present but skipped with
  `screens=0`.
- **Fix notes:** `inventory-interaction-smoke` now consolidates active-pack icon,
  crafting quick-move, right/left drag, and right-click split evidence behind
  one deterministic CLI. Each scenario validates numeric JSON and uses the
  normal screenshot path; all six real GL scenarios passed under
  `saves/inventory_interaction_smoke_l1/` when the display returned.
- **Next action:** use the reproducible command for future inventory parity
  slices; prioritize remaining crafting/inventory polish from observed player
  gaps rather than expanding this bug with unverified interaction rewrites.

### BUG-G007: World generation lacks distant richness

- **Status:** fixed
- **Affected area:** generation / settings UI / streaming
- **Observed:** terrain lacked distant biome silhouettes, visible landmarks,
  and profiling evidence that higher render distance avoided render-thread stalls.
- **Fix notes:** Settings exposes `[world].render_distance`, persists it, and
  applies changes to active chunk streaming without requiring a world reload.
  Biome-aware tall grass/wildflower ground cover, biome base-height silhouettes,
  deterministic landmark density coverage, bounded chunk submission, coalesced
  relighting, and section-budgeted remesh scheduling now make distant terrain
  readable without large streaming spikes.
- **Verification:** `benchmark-frame-streaming --render-distance 3 --frames 240
  --warmup-frames 30` measured avg 4.921 ms, p95 9.898 ms, max 14.145 ms;
  render distance 4 stress measured avg 5.803 ms, p95 12.521 ms, max 20.686 ms.

### BUG-S001: Creating/deleting worlds reused stale save state

- **Status:** fixed
- **Affected area:** world selection / persistence
- **Observed:** creating a world with a name whose save slug already existed could
  reuse the old save directory, including previous player inventory. Deleting a
  world could leave the cached world list stale.
- **Fix notes:** new worlds now use a unique save directory when the slug already
  exists, and world deletion goes through `WorldManager.delete_world()` which
  invalidates the saved-world cache.

### BUG-P001: Duplicate first-person hand render path

- **Status:** fixed
- **Affected area:** first-person HUD / viewmodel rendering
- **Observed:** first-person mode could show both the old 2D HUD hand/item
  overlay and the newer 3D viewmodel hand.
- **Fix notes:** legacy held-hand HUD overlay is now disabled; first-person hand
  and held block rendering comes from the 3D viewmodel path.

### BUG-P002: Local third-person avatar did not use player gait

- **Status:** fixed
- **Affected area:** perspective switching / local player rendering
- **Observed:** switching perspective showed a local player model that did not
  carry the same gait phase as the first-person player animation state.
- **Fix notes:** local avatar transient render world now receives an
  `AnimationState` derived from `PlayerAnimationSnapshot`.

### BUG-S002: User world settings were not persisted

- **Status:** fixed
- **Affected area:** settings persistence
- **Observed:** user settings writes saved window, camera, graphics, gameplay,
  audio, and controls, but not the `[world]` section.
- **Fix notes:** `save_user_settings()` now writes the world section, including
  render distance and generation/meshing settings.

### BUG-Q001: Project-wide Pyright is currently red

- **Status:** open
- **Affected area:** typing / quality gate
- **Observed:** `uv run pyright` reports 389 existing strict typing errors across engine, render, tests, and infrastructure (verified 2026-07-10).
- **Notes:** Not caused by Phase A docs/import-linter/composition skeleton. Do not mix a project-wide typing cleanup into architecture stabilization unless a Phase A change introduces new type errors.
- **Next action:** Fix incrementally when touching affected modules, or schedule a dedicated typing cleanup phase.

## Watchlist

### WATCH-A001: GameWindow still owns runtime construction

- **Status:** partial mitigation in progress
- **Affected area:** `render/window.py`
- **Notes:** Tracked by Phase A A4/A5. This is architectural debt rather than a user-visible bug.

### WATCH-A002: Controller window adapters are still too broad

- **Status:** investigating
- **Affected area:** `render/gameplay_controller.py`, `render/inventory_ui.py`, `render/network_controller.py`, and `render/input_state.py` now use window adapters instead of full `GameWindow`, but those adapters still expose broad window-like surfaces.
- **Notes:** Tracked by Phase D1 adapter narrowing and use-case extraction.

### WATCH-A003: DemoWorldRenderer owns world and rendering concerns

- **Status:** partial mitigation in progress
- **Affected area:** `render/world_scene.py`
- **Notes:** Tracked by Phase A A8. Storage/block registry/generator/streamer construction now starts in composition; external callers use runtime context, and renderer ownership fields are private. Renderer still calls world lifecycle internals until the next boundary split.
