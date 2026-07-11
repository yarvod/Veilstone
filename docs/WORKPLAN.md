# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (frame diagnostics) — after exposing all current bounded
streaming queues, identify whether the already-measured update or render stage is
the coarse frame bottleneck before adding finer subsystem timers.

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

### Phase N8: Coarse Frame Bottleneck Indicator

Promoted slice: update-vs-render bottleneck indication split out of `PERF-B002`;
this active scope was removed from that backlog entry in the same transition.

Цель: derive a deterministic coarse bottleneck label from the update/render
timings already owned by `RuntimePerfTracker`, expose it through the immutable
snapshot, and show it in F3 without inventing unmeasured subsystem data.

- [ ] Define update/render/tie/idle semantics in pure tracker tests and preserve
  the current frame timing behavior.
- [ ] Add the label to the existing F3 timing line through `RuntimePerfSnapshot`,
  without direct controller or renderer reads.
- [ ] Run focused/full gates and inspect a visible F3/F2 frame, then move N8 into
  CHANGELOG.

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
