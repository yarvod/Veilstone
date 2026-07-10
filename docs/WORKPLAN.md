# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — result and
crafting-input quick-move paths are complete; next work is one bounded
Minecraft-like cursor distribution interaction.

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

### Phase K5: Right-Drag Single-Item Distribution

Tracked issue: `BUG-G006`.

Цель: while carrying a cursor stack, right-drag across inventory/crafting slots
places at most one item into each distinct compatible slot, reusing existing
`InventoryLogic` right-click rules.

- [ ] Track distinct slots crossed during a right-button drag without putting
  inventory mutation rules into `InputHandler`.
- [ ] Reuse existing one-item right-click operations, skip incompatible/full
  slots, and stop cleanly when the cursor empties.
- [ ] Add input/logic coverage for distinct-slot distribution, revisits,
  incompatible slots, and unchanged click/left-drag behavior.
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
