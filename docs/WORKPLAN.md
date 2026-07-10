# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — distinct-slot
right-drag distribution is complete; next work is bounded capacity-aware
left-drag distribution.

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

### Phase K6: Left-Drag Even Distribution

Tracked issue: `BUG-G006`.

Цель: while carrying a cursor stack, left-drag across distinct compatible slots
distributes the stack as evenly as slot capacity allows and leaves any
unaccepted remainder on the cursor.

- [ ] Keep distinct target collection in gesture state, but perform capacity and
  item-count allocation through a narrow `InventoryLogic` operation.
- [ ] Distribute evenly across compatible inventory/crafting targets, respect
  max-stack limits, and retain any remainder on the cursor.
- [ ] Add pure allocation/input coverage for uneven counts, revisits,
  incompatible/full slots, and ordinary left-click behavior.
- [ ] Run real inventory/crafting GL smoke before committing.

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
