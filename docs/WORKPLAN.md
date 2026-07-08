# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Phase D architecture cleanup и grass/terrain
material coherence продолжать Minecraft-like visual/resource-pack polish через
render-only vegetation motion, не возвращая логику в `GameWindow` или
`DemoWorldRenderer`.

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

Promoted backlog: `R-B006`.

Цель: продолжить snapshot consolidation так, чтобы block/item visuals для chunk
meshing, held items, inventory icons, drops и remote held items не расходились
между разными render paths.

### Phase F1: Block/Item Model Snapshot Consolidation

- Findings: `item_block_texture_name()` already feeds inventory icons,
  `item_block_atlas_rect()` feeds dropped/entity/player held items, and
  first-person viewmodel uses `BlockModelSnapshot` face texture slots. Chunk
  meshing still reads raw `BlockDef` texture slots/material shape directly,
  making it the next consolidation target.
- Missing shared fields to evaluate next: atlas rects per face, render layer,
  render shape, wind motion, tint kind, and icon/default face policy.
- [x] Audit current block/item visual consumers: chunk meshing, first-person
  viewmodel, inventory icons, dropped items, entity held items.
- [ ] Define the smallest shared render-facing snapshot fields missing from
  existing `BlockModelSnapshot` / `ItemModelSnapshot`.
- [ ] Move one duplicated consumer path onto shared snapshot data with focused
  regression coverage.
- [ ] Real-game smoke for touched visual path: inventory/held/drop/remote path
  depending on selected slice, with screenshot or OpenGL draw check.

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
