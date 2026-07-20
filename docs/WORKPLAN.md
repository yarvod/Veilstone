# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (world presentation) — make the selected-block overlay
uniform and readable without translucent diagonal bands or face overdraw.

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

### Phase N17: Uniform Block Selection Overlay

Driven by the still-open `BUG-R007`, reproduced again in the visible N16 F2
capture.

Цель: keep the selected block outline readable while rendering every filled face
as one uniform subtle layer with no internal triangle bands or stacked alpha.

- [ ] Attribute the bands to highlight geometry, depth state, or blend state and
  lock the intended mesh/state contract with focused tests.
- [ ] Apply the smallest render-side fix without changing raycast/selection
  authority or ordinary chunk depth behavior.
- [ ] Run focused/full gates and a real visible `GameWindow` F2 pass from at
  least two selected-face angles; visually inspect both captures before resolving
  `BUG-R007`.

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
