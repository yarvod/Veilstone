# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — action feedback
priority is fixed; next work corrects a concrete Shift-click routing hazard
where incompatible target stacks can be swapped instead of skipped.

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

### Phase K8: Transactional Inventory Quick-Move Routing

Tracked issue: `BUG-G006`.

Цель: Shift-click between hotbar and main inventory merges matching stacks and
then uses empty targets, never swapping incompatible stacks or changing the
source item identity mid-operation.

- [ ] Replace `Inventory.move()` reuse in the quick-move path with a narrow
  merge-then-empty transfer that skips incompatible targets.
- [ ] Preserve source remainder when destination capacity is exhausted and leave
  unrelated stacks untouched.
- [ ] Add pure coverage for incompatible-first targets, partial capacity,
  hotbar-to-main and main-to-hotbar routing, and ordinary click/swap behavior.
- [ ] Run real Shift-click inventory GL smoke before committing.

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
