# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (RD12 low-end frame budget) — reproduce the locally
passing 720p `low_60` radius-12 contract on physical two-core hardware with the
complete 25x25 footprint loaded.

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

### Phase N15: RD12 60 FPS And Native Hot Paths

Promoted slices: measured native meshing/lighting kernels from `PERF-B004`, GPU
draw batching from `PERF-B005`, streaming light/fluid budgets from `PERF-B006`,
the local RD12 benchmark slice from `PERF-B007`, and benchmark-only streaming
stage attribution from `PERF-B002`. Those backlog entries now track only their
explicitly remaining scope.

Цель: measure a fully loaded radius-12 world with one generation and one
meshing worker, remove proven CPU/GPU stalls, and retain deterministic Python
fallbacks for every native kernel.

- [x] Extend `benchmark-frame-streaming` with standalone production-world CGL,
  full 625-chunk startup, update profiling, GPU finish/submit split, explicit
  draw counts, and optional PNG capture without misrepresenting it as a full
  `GameWindow`/UI pass.
- [x] Reduce update work with grouped priority drains, active-fluid chunks,
  chunk-coalesced remesh scheduling, and one-per-frame deferred unload saves.
- [x] Build optional Cython greedy-rectangle and sparse-light kernels with typed
  primitive arrays, Python fallbacks, `.pyi` contracts, differential tests, and
  wheel packaging. Full section meshing improved `1.8406 -> 1.6404 ms`; sparse
  light propagation improved `0.4061 -> 0.0791 ms`. Dense skylight remains on
  NumPy because the measured Cython path was slower.
- [x] Batch all opaque vertical sections per chunk and cull opaque/water batches
  whose complete AABB lies beyond enabled fog. RD12 `low_60` now submits `26`
  final draw calls and `73` visible sections instead of rendering the full 625-
  chunk GPU footprint; the inspected CGL capture has no missing geometry,
  shifted sections, border cracks, or culling/depth regressions:
  `saves/perf_rd12_n15/rd12_low60_acceptance_nice.png`.
- [x] Run the real-time-paced 600-frame 1280x720 RD12 walk on Apple M4 with 1+1
  lower-priority background workers and all 625 chunks loaded: p95 `6.235 ms`
  (`160.4 FPS`), p99 `9.411 ms` (`106.3 FPS`), max `15.918 ms`; generation,
  mesh, relight, and remesh queues all ended at `0`, with mesh queue max `34`.
- [x] Run complete deterministic gates: import contracts, Ruff, and format are
  green; unit result is `871 passed, 10 skipped`, full result is `887 passed, 38
  skipped`; focused Pyright is `0`, and the project-wide known-red `BUG-Q001`
  baseline remains `389` errors.
- [x] Attribute the RD12 maximum with disabled-by-default per-frame stage timing.
  Frame-coalesced GPU removals, indexed mesh revisions, latest-only replacement
  work, shared relight/remesh budgets, fog-range culling, per-chunk GPU batches,
  60 Hz benchmark pacing, and lower background-process priority reduced the
  profiled worst streaming-stage frame to `15.947 ms`; the clean contract then
  passed at max `15.918 ms` with no residual queue.
- [ ] Re-run the unchanged command plus visible F2 walk on representative
  physical two-core hardware. This external acceptance remains `PERF-B007`;
  Apple M4/CGL results cannot prove it.

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
