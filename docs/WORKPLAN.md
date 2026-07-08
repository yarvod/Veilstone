# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Phase D architecture cleanup продолжать
Minecraft-like visual/resource-pack polish, начиная с grass/terrain material
coherence и render-only vegetation motion, не возвращая логику в `GameWindow`
или `DemoWorldRenderer`.

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

### Phase E: Minecraft-Like Terrain Visual Polish

Promoted backlog: `R-B004`, `R-B005`.

Цель: сделать траву и terrain surfaces визуально ближе к Minecraft-like style и
подготовить render-only vegetation motion без накопления нового долга в
`GameWindow`.

### Phase E1: Grass/Terrain Material Coherence

- Findings: Faithful-style `grass_block_top`, `short_grass`, `oak_leaves`
  grayscale/tint-driven assets; current chunk mesh path has no tint channel,
  so renderer work must carry tint metadata beyond model snapshots.
- [ ] Audit default Faithful-style grass block texture routing, atlas rects,
  tint, mip/filter settings, terrain sampling paths.
- [x] Add focused tests proving grass terrain face texture/tint roles stay
  separate: tinted top, untinted side base, dirt bottom.
- [x] Add focused tests proving grass block inventory/held texture defaults to
  top without collapsing terrain side/bottom face paths.
- [ ] Add focused tests/fixtures proving atlas gutter/mipmap metadata is safe
  for terrain sampling.
- [ ] Implement Minecraft-like grass field smoothing distance-safe sampling
  through render/material snapshots renderer helpers, not window/controller
  state.
- [ ] Verify default Faithful-style packs in real app: walk on grass, inspect
  shallow camera angles, tree shadows, grass color continuity, capture
  screenshots when display is available.

### Phase E3: Render-Only Vegetation Motion

- [ ] Define render-facing vegetation wind data grass/leaves/plants that
  preserves deterministic gameplay/collision state.
- [ ] Add subtle quality-gated grass/leaf sway in renderer/material code without
  changing domain block definitions or resource-pack folder routing.
- [ ] Add tests for animation parameter plumbing and disabled/low-quality
  fallback behavior without OpenGL.
- [ ] Real-game smoke: inspect grass/leaves near spawn, verify shadows remain
  readable and FPS/debug overlay stays sane.

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
