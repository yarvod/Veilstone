# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory icon depth, `BUG-G006`) — the shared
block/item snapshot layer already exists; next work should make block items read
as compact isometric objects without moving inventory rules into render code.

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

### Phase K1: Isometric Block Inventory Icons

Tracked issue: `BUG-G006`; follows completed snapshot backlog `R-B006`.

Цель: reuse `ItemModelSnapshot` face texture slots to give block items a
Minecraft-like isometric silhouette in inventory/hotbar/crafting UI while
keeping non-block item icons and inventory behavior unchanged.

- [ ] Build an isometric block-icon composer from the existing top/side texture
  slots; preserve alpha and pixel-art sampling.
- [ ] Keep resource/fluid-container fallback icons unchanged and avoid adding
  inventory/domain rules to the renderer.
- [ ] Add focused image/snapshot tests for face selection, silhouette, and
  transparent background.
- [ ] Run the real inventory GL smoke and capture an inventory/hotbar screenshot
  before committing.

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
