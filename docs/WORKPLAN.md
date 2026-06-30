# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Phase D architecture cleanup перейти к
Minecraft-like visual/resource-pack polish, начиная с травы, terrain material
coherence и F3 diagnostics, не возвращая логику в `GameWindow` или
`DemoWorldRenderer`.

Выполненная история живёт в `docs/CHANGELOG.md`; баги и watchlist —
в `docs/BUGS.md`; идеи не в работе — в `docs/BACKLOG.md`.

## Product Direction

Новые player-facing фичи должны идти через явные runtime/use-case/snapshot
границы:

- `GameWindow` остаётся тонкой Pyglet оболочкой и composition-facing адаптером;
- gameplay mutation, audio events, networking, settings и storage не должны
  расползаться по render-классам;
- visual/resource-pack work uses Minecraft-style content paths under
  `resource_packs/default/assets/<namespace>/textures|sounds/...`;
- new texture/audio assets must be added through the default resource pack
  folder routing, not hard-coded legacy fallbacks;
- real-game smoke checks обязательны для UI/render/audio/controls changes:
  launch the real app, interact with the feature, capture screenshots when the
  display is available, and record blocker details when Cocoa/OpenGL display is
  unavailable;
- focused Pyright обязателен для затронутых typed boundaries; full Pyright пока
  tracked как known-red `BUG-Q001`.

## Current Phase

### Phase E: Minecraft-Like Terrain Visual Polish And Diagnostics

Promoted backlog: `R-B004`, `DX-B001`, `R-B005`.

Цель: сделать траву и terrain surfaces визуально ближе к Minecraft-like style,
дать F3 enough diagnostics для проверки FPS/координат/чанков/биомов/очередей и
подготовить render-only vegetation motion без накопления нового долга в
`GameWindow`.

### Phase E1: Grass/Terrain Material Coherence

- Findings: Faithful-style `grass_block_top`, `short_grass`, and `oak_leaves`
  are grayscale/tint-driven assets; current chunk mesh path has no tint channel,
  so renderer work must carry tint metadata beyond model snapshots.
- [ ] Audit default and Faithful-style grass block texture routing, atlas rects,
  tint, mip/filter settings, and terrain sampling paths.
- [ ] Add focused tests/fixtures proving grass material lookup, tint, atlas
  gutter/mipmap metadata, and inventory/held-item texture paths stay separate.
- [ ] Implement Minecraft-like grass field smoothing or distance-safe sampling
  through render/material snapshots or renderer helpers, not window/controller
  state.
- [ ] Verify default and Faithful-style packs in the real app: walk on grass,
  inspect shallow camera angles, tree shadows, grass color continuity, and
  capture screenshots when display is available.

### Phase E2: Minecraft-Like F3 Diagnostics

- [ ] Extend cached HUD debug snapshots with practical diagnostics: FPS/frame
  timing, precise player coordinates, block/chunk coordinates, facing, biome or
  terrain profile, render distance, chunk/mesh queues, visible chunks, and
  active resource pack.
- [ ] Keep diagnostics low-frequency/cached so F3 does not perform expensive
  per-frame reads.
- [ ] Add unit coverage for debug snapshot content without constructing Pyglet
  or ModernGL.
- [ ] Real-game smoke F3 overlay: toggle F3, walk, inspect FPS/coords/chunk
  values updating, and save screenshot evidence when display is available.

### Phase E3: Render-Only Vegetation Motion

- [ ] Define render-facing vegetation wind data for grass/leaves/plants that
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
