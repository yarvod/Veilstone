# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — odd-stack
right-click rounding now matches crafting; next work fixes the separate
single-item inventory right-click no-op.

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

### Phase K10: Single-Item Right-Click Pickup

Tracked issue: `BUG-G006`.

Цель: right-clicking a single inventory item picks it up onto the cursor and
clears the source slot, matching crafting-grid and Minecraft behavior.

- [ ] Separate empty-slot handling from single-item pickup in the inventory
  split/right-click path.
- [ ] Prove inventory and crafting-grid single-item pickup produce identical
  cursor/source state.
- [ ] Preserve odd/even split rounding, right-click placement, and drag behavior.
- [ ] Run real inventory GL smoke when a display is available; otherwise record
  the same verified environment limitation and closest deterministic coverage.

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
