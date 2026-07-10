# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — block icons are
isometric and follow live resource-pack switches; next work is one narrow
Minecraft-like crafting-result interaction without widening render ownership.

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

### Phase K3: Crafting Result Quick-Move

Tracked issue: `BUG-G006`.

Цель: make Shift-click on a valid crafting result transfer crafted output into
inventory through `InventoryLogic`, while keeping input handling and rendering
free of recipe/inventory mutation rules.

- [ ] Carry the Shift modifier from result-slot input into a narrow crafting
  quick-move operation.
- [ ] Craft repeatedly only while the recipe still matches and the full result
  stack can be accepted; never consume ingredients for rejected output.
- [ ] Add pure logic coverage for normal transfer, repeated transfer, full
  inventory, stack limits, and unchanged ordinary result clicks.
- [ ] Run real crafting/inventory GL smoke before committing.

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
