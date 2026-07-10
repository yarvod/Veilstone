# Veilstone — Рабочий План

## Overview

Активная цель: Phase J (water surface visual quality, `R-B009`) — highlights,
ripple reflections, quality gating, and reproducible visual/physics smoke are
implemented; next work should add a shoreline cue without mixing simulation
fixes into render/UI classes.

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

### Phase J5: Shoreline Water Readability

Promoted backlog: `R-B009`.

Цель: make water edges read clearly against terrain with a detail-gated,
render-only shoreline cue while preserving the low-cost `low_60` path and
stable item buoyancy from `BUG-G008`.

- [ ] Expose a render-facing shoreline factor from water meshing without
  changing fluid source/level simulation.
- [ ] Add a subtle shoreline tint/foam cue gated by `water_detail`, preserving
  the exact cheaper `low_60` fallback.
- [ ] Extend focused mesh/shader coverage for the shoreline contract.
- [ ] Run `water-surface-smoke` on real GL and verify both visual tiers, nonzero
  water mesh geometry, and stable item metrics before committing.

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
