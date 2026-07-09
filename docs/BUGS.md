# Known Bugs & Issues

This file tracks active bugs, regressions, flaky tests, and unresolved quality issues. Completed historical fixes belong in `docs/CHANGELOG.md`.

## Open

### BUG-T001: test_ui_renderer fails when run after other render tests

- **Status:** open
- **Affected area:** tests / pyglet UI renderer test isolation
- **Observed:** `uv run pytest tests/unit/render` fails 8 `test_ui_renderer.py`
  tests (widget layout/callback assertions), while the same file passes in
  isolation and the `-m unit` gate stays green. Reproduced on a clean `main`
  checkout, so it is a pre-existing test-order interaction, likely shared
  pyglet/GL global state from earlier render tests.
- **Reproduction:** `uv run pytest tests/unit/render` (fails) vs
  `uv run pytest tests/unit/render/test_ui_renderer.py` (passes).

### BUG-R006: Shadow artifacts on terrain surfaces

- **Status:** open
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
- **Next action:** inspect receiver projected coordinates, depth compare,
  bias/filtering, and shadow-matrix bounds before changing material-preview
  lighting or later `R-B009` water work.

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
- **Observed:** inventory still lacks 3D item icons and full crafting UX polish.
- **Fix notes:** stack counts, hover names, drag-and-drop movement, and selected
  and drag slot states are present; inventory UI logic now refreshes the active
  world inventory reference after creating or switching worlds so stale saved
  items cannot leak into the new-world UI state.
- **Next action:** add render-facing item icon/model snapshots and improve slot
  interaction incrementally without moving inventory rules into render code.

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
- **Observed:** `uv run pyright` reports 382 existing strict typing errors across engine, render, tests, and infrastructure.
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
