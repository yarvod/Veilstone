# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (measured lighting optimization) — RD4 update profiling
attributes the dominant cost to NumPy light propagation, so optimize only its
temporary-array churn before considering other streaming subsystems.

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

### Phase N11: Lighting Propagation Scratch-Buffer Reuse

Promoted slice: `_propagate_light` temporary-allocation reduction split out of
`PERF-B001`; this active scope was removed from that backlog entry in the same
transition.

Цель: reuse bounded NumPy scratch buffers inside the measured lighting hotspot
without changing skylight/block-light results, early convergence, dirty flags,
or chunk-boundary propagation behavior.

- [ ] Preserve exact propagation results across empty, opaque, emissive,
  cross-chunk, and randomized deterministic fixtures before changing buffers.
- [ ] Reuse per-call uint8 scratch arrays inside `_propagate_light` while keeping
  the 15-step bound and convergence semantics explicit.
- [ ] Compare lighting microbenchmark plus unprofiled RD3/RD4 p95/max, then run a
  visible lighting/F2 pass and move N11 into CHANGELOG only if parity and runtime
  evidence both hold.

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
