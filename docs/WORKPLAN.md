# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (benchmark evidence) — aggregate the new coarse
update/render classification across deterministic RD3/RD4 streaming runs before
choosing the next optimization target.

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

### Phase N9: Streaming Bottleneck Distribution

Promoted slice: RD3/RD4 bottleneck-distribution measurement split out of
`PERF-B001`; this active scope was removed from that backlog entry in the same
transition.

Цель: make `benchmark-frame-streaming` report how many measured frames are
update-bound, render-bound, balanced, or idle, using the same classification as
F3 so the next performance phase follows evidence rather than a single frame.

- [ ] Reuse one pure public classification rule in tracker and benchmark paths;
  do not duplicate thresholds or add renderer/window ownership.
- [ ] Add deterministic distribution formatting and focused tests independent of
  Pyglet/OpenGL.
- [ ] Run RD3/RD4 benchmarks, compare p95/max and distributions, then move N9
  into CHANGELOG and select the next measured bottleneck slice.

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
