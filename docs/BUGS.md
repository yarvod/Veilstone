# Known Bugs & Issues

This file tracks active bugs, regressions, flaky tests, and unresolved quality issues. Completed historical fixes belong in `docs/CHANGELOG.md`.

## Open

### BUG-G001: Player cannot reliably leave water onto shore

- **Status:** open
- **Affected area:** player physics / water collision
- **Observed:** player can swim upward, but transitioning from water onto nearby
  land is unreliable or blocked.
- **Next action:** add a focused shore-exit regression test around water,
  collision, step-up, and jump/swim movement; fix movement rules without adding
  render/window dependencies.

### BUG-G002: Water flow surface looks interrupted after block breaks

- **Status:** open
- **Affected area:** fluid simulation / water rendering
- **Observed:** flowing water after removing blocks can look visually broken or
  choppy instead of forming a smooth Minecraft-like continuous flow surface.
- **Next action:** separate simulation correctness from render smoothing; first
  verify fluid levels/dirty propagation, then add surface interpolation if state
  is correct.

### BUG-G003: Footstep audio and movement presentation are not unified

- **Status:** investigating
- **Affected area:** player feel / audio / animation
- **Observed:** walking camera bob, footstep sounds, player body, and future hand
  animation do not share one gait phase. Footsteps were also too loud by default.
- **Fix notes:** default footstep and block-step resource gains were lowered.
- **Next action:** introduce a gait/animation state that drives bob, sound, body,
  and viewmodel from the same cadence.

### BUG-G004: Mob walk animations slide and do not match locomotion

- **Status:** open
- **Affected area:** entity animation / mobs
- **Observed:** cow and zombie walk loops do not convincingly match actual leg
  placement, speed, turning, or step contact.
- **Next action:** drive animation phase from entity velocity and grounded state;
  add tests for phase advancement and idle reset.

### BUG-G005: Leaf/resource-pack transparency is not rendered as cutout

- **Status:** open
- **Affected area:** texture packs / block rendering
- **Observed:** textures with transparent regions, such as Faithful-style leaves,
  do not yet show the world through holes like Minecraft leaves.
- **Next action:** add an alpha-tested/cutout block render path and verify depth
  behavior on leaf blocks.

### BUG-G006: Inventory UI is functional but not Minecraft-polished

- **Status:** open
- **Affected area:** UI / inventory / item rendering
- **Observed:** inventory lacks 3D item icons, stack-count corner overlays,
  polished hover names, drag-and-drop movement, and full crafting UX.
- **Next action:** add render-facing item icon snapshots and improve slot
  interaction incrementally without moving inventory rules into render code.

### BUG-G007: World generation lacks distant richness and settings control

- **Status:** open
- **Affected area:** generation / settings UI / streaming
- **Observed:** terrain lacks enough distant fields, biome filling, grass,
  flowers, and in-game render-distance control.
- **Next action:** add Settings UI render-distance control and schedule generation
  feature-density passes with deterministic tests.

### BUG-Q001: Project-wide Pyright is currently red

- **Status:** open
- **Affected area:** typing / quality gate
- **Observed:** `uv run pyright` reports 549 existing strict typing errors across engine, render, tests, and infrastructure.
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
