# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (performance) — keep RD12 streaming bounded during
realistic sustained player movement, with stable 60 FPS and no accumulating
generation, relight, remesh, or upload queues.

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

### Phase N20: Sustained RD12 Movement Streaming

Promoted from the remaining `PERF-B001` scope after N19 proved imported foliage
topology correct.

Цель: preserve the accepted stationary RD12 `low_60` frame budget while moving
at normal gameplay speed, and keep loaded coverage plus all streaming queues
bounded after warmup. Native Cython greedy/light kernels remain optional fast
paths with deterministic Python fallbacks.

- [ ] Measure RD12 at normal walk/sprint rates separately from the existing
  45-block/s stress path; attribute any queue growth by streaming stage.
- [ ] Bound or coalesce the dominant stage without weakening collision-critical
  priority, save correctness, or stationary visibility.
- [ ] Verify native kernels are actually loaded in the benchmark environment and
  compare against their Python fallbacks where practical.
- [ ] Pass 1280x720 RD12 `low_60` at stable 60 FPS with bounded end queues, then
  run full gates and visible gameplay when macOS exposes an active display.

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
