# Veilstone — Рабочий План

## Overview

Активная цель: Phase J (water surface visual quality, `R-B009`) — first crest
highlight slice is implemented and smoke-tested; next work should deepen water
motion/reflection cues without mixing simulation fixes back into render/UI
classes.

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

### Phase J2: Water Motion And Reflection Cues

Promoted backlog: `R-B009`.

Цель: build on the new crest highlights with richer gameplay-readable water
motion/reflection cues while preserving stable item buoyancy from `BUG-G008`.

- [ ] Evaluate whether water needs quality-profile gating for extra ripple/glint
  cost on `low_60` versus `high`/`cinematic`.
- [ ] Add a stronger near-surface ripple/reflection cue that remains readable
  from shallow camera angles.
- [ ] Keep water simulation untouched unless a fresh `BUG-G008` regression is
  observed.
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
