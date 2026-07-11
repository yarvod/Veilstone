# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (swimming feedback) — player input regressions are closed
with repeatable visible coverage; the next small slice gives continuous swimming
its own soft audio cadence instead of relying only on water enter/exit splashes.

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

### Phase N1: Swimming Stroke Audio Polish

Promoted backlog item: `WORLD-B005`.

Цель: continuous swimming emits a soft Minecraft-like stroke cadence distinct
from water enter/exit and landing sounds, through typed gameplay/application
events and resource-pack audio routing rather than render-only timing state.

- [ ] Reuse renderer-independent swimming/movement cadence state or add the
  smallest explicit event state needed; do not put cadence timers in
  `GameWindow`.
- [ ] Add a typed swim-stroke event and route it through the existing audio event
  adapter to a default resource-pack sound location.
- [ ] Add deterministic cadence/no-spam tests for moving, stationary, entering,
  exiting, and grounded player states.
- [ ] Run a visible real-water movement pass, listen for distinct repeated soft
  strokes without enter/exit spam, capture through F2, and inspect the frame.

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
