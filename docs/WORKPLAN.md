# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (performance diagnostics) — expose generation, GPU upload,
and dirty-work counters through the existing runtime performance snapshot so F3
can explain future frame spikes without render-layer introspection.

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

### Phase N21: Runtime Chunk Pipeline Diagnostics

Promoted from `PERF-B002` after N20 established bounded RD12 sprint streaming.

Цель: extend `RuntimePerfSnapshot` rather than create a second diagnostics path;
sample the missing counters at bounded frequency and keep the HUD a passive
snapshot consumer.

- [ ] Map existing streamer/mesh/cache state into generation jobs, completed GPU
  uploads, and dirty/deferred-save counts without filesystem reads per frame.
- [ ] Extend application-facing snapshot contracts and focused tests before
  changing F3 labels.
- [ ] Keep HUD sampling bounded and verify diagnostics collection does not regress
  the accepted RD12 `low_60` frame budget.
- [ ] Run full gates and visible F3 verification when macOS exposes an active
  display.

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
