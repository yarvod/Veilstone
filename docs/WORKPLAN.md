# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (world presentation) — make broad grass surfaces read as
coherent ground cover at shallow camera angles without sacrificing pixel-sharp
inventory and held-item rendering.

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

### Phase N18: Coherent Grass Surface Tiling

Promoted from `R-B004` after N17 proved `BUG-R007` obsolete.

Цель: reduce harsh per-block repetition across large grass fields while keeping
resource-pack texture resolution, atlas isolation, and non-terrain item sampling
unchanged.

- [ ] Capture a deterministic shallow-angle baseline and attribute visible
  repetition to texture content, UV phase, biome tint, filtering, or lighting.
- [ ] Apply the smallest terrain-only improvement; do not blur inventory,
  held-item, entity, or UI textures and do not add extra chunk draw calls.
- [ ] Add focused render/mesh coverage and compare RD12 `low_60` frame pacing
  against the accepted N15 budget.
- [ ] Run full gates and a visible `GameWindow` F2 pass when macOS exposes an
  active display; visually inspect the before/after evidence.

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
