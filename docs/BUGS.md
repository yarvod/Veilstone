# Known Bugs & Issues

This file tracks active bugs, regressions, flaky tests, and unresolved quality issues. Completed historical fixes belong in `docs/CHANGELOG.md`.

## Open

### BUG-Q001: Project-wide Pyright is currently red

- **Status:** open
- **Affected area:** typing / quality gate
- **Observed:** `uv run pyright` reports 547 existing strict typing errors across engine, render, tests, and infrastructure.
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
- **Notes:** Tracked by Phase A A8. Storage/block registry/generator/streamer construction now starts in composition; runtime rebuild, initial loading, WorldManager save/restore, and NetworkController structure storage use runtime context. Renderer still exposes and calls world lifecycle fields directly.
