# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (update attribution) — RD3/RD4 streaming is conclusively
update-bound, so profile the measured update path before choosing any generation,
lighting, meshing, upload, or gameplay optimization.

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

### Phase N10: RD4 Update-Stage Profile Attribution

Promoted slice: deterministic RD4 update-path profiling split out of
`PERF-B001`; this active scope was removed from that backlog entry in the same
transition.

Цель: attribute the update-bound RD4 benchmark to concrete Veilstone functions
after warmup, separating generation/lighting/meshing/upload and unrelated
gameplay work without changing runtime behavior during this measurement phase.

- [ ] Add or use a reproducible profiler mode that excludes startup/warmup and
  reports Veilstone-owned cumulative/self time with bounded output.
- [ ] Profile the same RD4 movement workload, identify the dominant update
  function chain, and verify the profiler itself does not alter normal benchmark
  output or architecture boundaries.
- [ ] Record evidence, select one narrow optimization slice, and move N10 into
  CHANGELOG; do not optimize several subsystems speculatively.

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
