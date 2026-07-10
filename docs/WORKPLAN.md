# Veilstone — Рабочий План

## Overview

Активная цель: Phase L (reference gameplay verification, `WORLD-B004`) — core
inventory click/drag/quick-move parity slices are complete; next work replaces
their ad-hoc `/tmp` capture scripts with one reproducible inventory smoke tool.

Выполненная история живёт в `docs/CHANGELOG.md`; баги и watchlist — в
`docs/BUGS.md`; идеи не в работе — в `docs/BACKLOG.md`.

## Product Direction

Новые player-facing фичи должны идти через явные runtime/use-case/snapshot
границы:

- `GameWindow` остаётся тонкой Pyglet оболочкой и composition-facing адаптером;
- gameplay mutation, audio events, networking, settings и storage не должны
  расползаться по render-классам;
- visual/resource-pack work uses Minecraft-style content paths under
  `resource_packs/default/assets/<namespace>/textures|sounds/...`;
- new texture/audio assets added through default resource pack folder routing,
  not hard-coded legacy fallbacks;
- real-game smoke checks обязательны для UI/render/audio/controls changes:
  launch real app, interact feature, capture screenshots display available,
  record blocker details Cocoa/OpenGL display unavailable;
- focused Pyright обязателен для затронутых typed boundaries; full Pyright пока
  tracked как known-red `BUG-Q001`.

## Current Phase

### Phase L1: Reproducible Inventory Interaction Smoke

Tracked backlog: `WORLD-B004`; coverage source: completed `BUG-G006` slices.

Цель: provide one deterministic CLI smoke command that prepares representative
inventory/crafting state, exercises a selected interaction scenario, and writes
numeric JSON evidence plus a screenshot when a display is available.

- [ ] Add `inventory-interaction-smoke` CLI/bootstrap routing with a narrow tool
  module rather than growing `GameWindow`.
- [ ] Encode deterministic scenarios for resource-pack icons, crafting/result
  quick-move, right/left drag, and right-click split with numeric assertions.
- [ ] Write stable JSON metadata and capture through the normal screenshot flow;
  return an explicit skip when no display exists.
- [ ] Add unit tests for scenario metadata/validation and run the real command
  when a display is available.

## Check Gate

Run before commits unless narrower WIP checkpoint explicitly documented:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pyright
```

`pyright` currently expected to fail only known `BUG-Q001` baseline.
