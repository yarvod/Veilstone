# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (physical two-core acceptance) — use the completed runtime
pipeline diagnostics to remove the measured RD12 update/meshing backlog on the
Windows two-core target while preserving the readable `low_60` scene.

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

### Phase N22: Physical Two-Core 60 FPS Acceptance

Promoted from `PERF-B007` after N21 exposed the runtime generation, GPU upload,
dirty, and deferred-save counters on the Windows target.

Baseline: the unchanged 600-frame 1280x720 RD12 `low_60` walk with one generation
and one meshing worker measures average `14.637 ms`, p95 `33.474 ms`, p99
`37.133 ms`, update p95 `28.766 ms`, and render p95 `5.942 ms`. The final mesh
queue remains at `115`, so the current blocker is update/meshing throughput rather
than GPU submission.

- [ ] Profile the update-side queue growth with streaming-stage samples and the
  N21 counters; identify generation, relight, remesh scheduling, or Python mesh
  fallback cost before changing budgets.
- [ ] Keep main-thread work bounded while draining the sustained mesh queue on one
  generation and one meshing worker; avoid hiding backlog with a shorter route.
- [ ] Repeat the exact 600-frame RD12 command and require p95 below `16.7 ms` with
  bounded/end-drained queues, or record the remaining measured subsystem blocker.
- [ ] Run full gates plus visible movement/F3/F2 acceptance on the physical target.

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
