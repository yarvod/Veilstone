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

Current Windows baseline: the unchanged 600-frame 1280x720 RD12 `low_60` walk
with one generation and one meshing worker measures average `5.410 ms`, p95
`11.706 ms`, p99 `15.906 ms`, update p95 `8.805 ms`, and render p95 `3.795 ms`.
Fog-hidden RD12 chunks remain generated and loaded, while mesh work is bounded
to the exact fog-reachable AABB horizon and cross-chunk relight to its 15-block
propagation radius. Cross-chunk propagation is sliced one exact NumPy iteration
per frame and the unchanged horizon is cached between chunk transitions.
Executor work ends at `2`, relight at `0`, and render-owned remesh at `15`;
both p95 and p99 now clear 60 FPS, while the terminal remesh tail and `24.873 ms`
worst frame remain open.

- [x] Profile the update-side queue growth: streaming relight measured p95
  `31.791 ms`/max `72.647 ms`; the Python mesher also cannot consume duplicate
  intermediate boundary requests at the sprint intake rate.
- [x] Bound ProcessPool meshing to `2 × workers` in-flight/replacement requests
  and wait for expected cardinal neighbors before building a chunk snapshot.
  Executor queue max fell from `115` to `2`; inspected frame:
  `saves/rd12_windows_2core_n22_bounded_only.png`. Visible movement/F3/F2:
  `saves/n22_bounded_input_lifecycle/screenshots/veilstone_20260721_143938.png`.
- [x] Bound main-thread mesh/relight intake to fog-reachable work without reducing
  RD12 generation or loaded coverage. Average improved `12.736 -> 5.895 ms`, p95
  `33.509 -> 12.286 ms`, and the render-owned remesh tail `103 -> 9`. Inspected
  frame: `saves/rd12_windows_2core_n22_exact_horizon.png`.
- [x] Repeat the exact 600-frame RD12 command and get p95 and p99 below `16.7 ms`:
  p95 is `11.706 ms`/`85.4 FPS`, p99 `15.906 ms`/`62.9 FPS`, and max
  `24.873 ms`. Inspected frame:
  `saves/rd12_windows_2core_n22_incremental_cached.png`.
- [x] Split cross-chunk relight propagation into one result-equivalent iteration
  per frame and cache the fog horizon while center/quality state is unchanged.
  The synchronous `45.794 ms` worst frame fell to `24.873 ms`; an active job is
  included in the public/F3 relight queue count.
- [ ] Drain the final render-owned remesh tail (`15`) without hiding it in the
  executor; next measure section-granular relight remesh versus full-chunk rebuilds.
- [x] Run full gates plus visible movement/F3/F2 acceptance for the fog-horizon
  and incremental-relight slices on the physical target. Latest visible evidence:
  `saves/n22_incremental_input_lifecycle/screenshots/veilstone_20260721_151909.png`.

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
