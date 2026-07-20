# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (world presentation) — make imported Minecraft-style
grass and foliage use the correct cube, overlay, cutout, and crossed-plane model
semantics instead of distorted sheets.

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

### Phase N19: Resource-Pack Grass And Foliage Models

Promoted from `R-B002` after N18 completed terrain-only grass sampling.

Цель: reproduce a concrete imported-pack distortion, correct only the missing
resource-location/model metadata or sampling contract, and preserve default-pack
geometry and chunk frame budgets.

- [ ] Import the existing Minecraft-style fixture/pack and capture the exact
  distorted grass, leaves, or crossed-plant case before changing model logic.
- [ ] Trace resource aliases, grass side overlay composition, tint, alpha mode,
  and render shape from importer through model snapshot and mesh lookup.
- [ ] Apply the smallest data-driven fix with pack-specific regression coverage;
  avoid pack-name conditionals and texture-content heuristics.
- [ ] Run focused/full gates, production GL comparison, and visible F2 acceptance
  when macOS exposes an active display.

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
