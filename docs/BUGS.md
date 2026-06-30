# Known Bugs & Issues

This file tracks active bugs, regressions, flaky tests, and unresolved quality issues. Completed historical fixes belong in `docs/CHANGELOG.md`.

## Open

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

- **Status:** open
- **Affected area:** generation / settings UI / streaming
- **Observed:** terrain still needs profiling evidence that higher render
  distance does not stall render-thread work.
- **Fix notes:** Settings now exposes `[world].render_distance`, persists it,
  and applies changes to active chunk streaming without requiring a world reload.
  Biome-aware tall grass/wildflower ground cover, biome base-height silhouettes,
  and deterministic landmark density coverage now make distant terrain more
  readable.
- **Next action:** profile render distance above two chunks and split
  generation/meshing/upload stalls into bounded streaming work where needed.

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
- **Observed:** `uv run pyright` reports 517 existing strict typing errors across engine, render, tests, and infrastructure.
- **Notes:** Not caused by Phase A docs/import-linter/composition skeleton. Do not mix a project-wide typing cleanup into architecture stabilization unless a Phase A change introduces new type errors.
- **Next action:** Fix incrementally when touching affected modules, or schedule a dedicated typing cleanup phase.

## Watchlist

### WATCH-A001: GameWindow still owns runtime construction

- **Status:** partial mitigation in progress
- **Affected area:** `render/window.py`
- **Notes:** Tracked by Phase A A4/A5. This is architectural debt rather than a user-visible bug.

### WATCH-A002: Controllers still receive full GameWindow

- **Status:** investigating
- **Affected area:** `render/gameplay_controller.py`, `render/hud_controller.py`, `render/network_controller.py`
- **Notes:** Tracked by Phase A A6/A7.

### WATCH-A003: DemoWorldRenderer owns world and rendering concerns

- **Status:** partial mitigation in progress
- **Affected area:** `render/world_scene.py`
- **Notes:** Tracked by Phase A A8. Storage/block registry/generator/streamer construction now starts in composition; external callers use runtime context, and renderer ownership fields are private. Renderer still calls world lifecycle internals until the next boundary split.
