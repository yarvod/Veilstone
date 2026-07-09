# Veilstone — Рабочий План

## Overview

Активная цель: Phase J (water surface visual quality, `R-B009`) — shadow
artifact cleanup is fixed and documented; next work improves water readability
without mixing simulation fixes back into render/UI classes.

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

### Phase J: Water Surface Visual Quality

Promoted backlog: `R-B009`.

Цель: make water read more like water at gameplay distance: clearer surface
highlights/reflection cues, less flat movement, and no regression to the stable
item buoyancy fixed in `BUG-G008`.

- [ ] Inspect current water mesh/shader path and capture baseline water
  screenshots with floating item drops visible.
- [ ] Add low-cost surface animation/normal or highlight cues behind quality
  settings where appropriate.
- [ ] Verify item drops still rise to and settle at the water surface.
- [ ] Run real gameplay water smoke with screenshot path and item stability
  metrics before committing.

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
