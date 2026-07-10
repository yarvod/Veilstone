# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — transactional
Shift-click routing is complete; next work aligns odd-stack inventory right-click
splitting with crafting/Minecraft ceil-half behavior.

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

### Phase K9: Odd-Stack Right-Click Split Parity

Tracked issue: `BUG-G006`.

Цель: right-click pickup from an odd inventory stack takes the larger half and
leaves the smaller half, matching the existing crafting-grid behavior.

- [ ] Correct `Inventory.split()` rounding without changing even-stack or
  single-item behavior.
- [ ] Prove inventory and crafting-grid odd splits produce the same cursor/source
  counts.
- [ ] Preserve right-click placement, drag distribution, and max-stack behavior.
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
