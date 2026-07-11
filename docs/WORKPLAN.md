# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (streaming priority) — backlog now contains only verified
open remainder; the next small slice makes bounded relight/remesh work prefer
near-camera chunks without discarding FIFO stability or existing budgets.

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

### Phase N4: Camera-Distance Streaming Queue Priority

Promoted slice: `PERF-B003`.

Цель: existing bounded stream relight/remesh queues drain nearer chunk work
before farther work, while preserving insertion order for equal priority and
leaving visibility/collision-critical policy as explicit future backlog scope.

- [ ] Add a renderer-independent bounded priority drain with deterministic FIFO
  ties and no mutation beyond the selected budget.
- [ ] Feed current camera/chunk distance into relight and remesh scheduling
  without moving ownership into `GameWindow` or changing generation authority.
- [ ] Cover negative coordinates, equal-distance ties, zero budget, and queue
  remainder order with focused tests.
- [ ] Run frame-streaming checks plus a visible walking/F3 pass at render distance
  above two, inspect F2 evidence, and compare queue behavior for regressions.

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
