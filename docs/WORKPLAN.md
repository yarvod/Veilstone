# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — resource-pack
icons and transactional result quick-move are complete; next work is one narrow
crafting-input quick-move interaction owned by `InventoryLogic`.

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

### Phase K4: Crafting Input Quick-Move

Tracked issue: `BUG-G006`.

Цель: make Shift-click on a crafting input return that stack to inventory
without routing it through the cursor, while keeping capacity/remainder rules in
`InventoryLogic`.

- [ ] Carry the Shift modifier from crafting-slot input into a narrow quick-move
  operation without changing ordinary left/right click behavior.
- [ ] Merge into existing inventory stacks first, preserve any unaccepted
  remainder in the crafting slot, and leave the cursor unchanged.
- [ ] Add pure logic/input coverage for full transfer, partial/full inventory,
  and unchanged ordinary crafting clicks.
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
