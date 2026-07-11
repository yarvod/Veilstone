# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (streaming priority) — bounded relight/remesh work now
prefers near and camera-visible chunks; the final promoted slice protects
collision-critical work needed by local player physics.

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

### Phase N6: Collision-Critical Streaming Queue Priority

Promoted slice: `PERF-B003`.

Цель: queued chunks/sections required for the local player's collision envelope
receive an explicit narrow priority signal without bypassing budgets, duplicating
physics rules in render code, or weakening distance/visibility determinism.

- [ ] Find the existing player/collision-area ownership seam and derive a compact
  set or predicate of collision-critical chunk coordinates outside render rules.
- [ ] Compose collision need with distance and visibility priority while keeping
  per-frame budgets and FIFO order inside equal scores.
- [ ] Cover boundary/negative coordinates, unavailable collision data, and
  world-scene queue integration without constructing `GameWindow` in unit tests.
- [ ] Repeat RD3/RD4 benchmarks and visible movement across a chunk boundary,
  inspect F2/F3 evidence, then move N6 into CHANGELOG.

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
