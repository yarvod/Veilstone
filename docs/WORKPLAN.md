# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory icon polish, `BUG-G006`) — block items now
render as compact isometric icons; next work should source those faces from the
active resource-pack atlas without widening inventory/controller ownership.

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

### Phase K2: Resource-Pack-Aware Inventory Icons

Tracked issue: `BUG-G006`; related resource-pack gap: `R-B002`.

Цель: make inventory/hotbar/crafting block icons consume the active block atlas
and refresh after a resource-pack switch while preserving the pure isometric
composer and existing non-block fallbacks.

- [ ] Replace the procedural-default atlas lookup in `create_item_icons()` with
  a narrow active-atlas image/UV input owned by render composition.
- [ ] Refresh existing hotbar/inventory/crafting/cursor icon images after
  resource-pack apply without reconstructing inventory gameplay state.
- [ ] Add focused fake-atlas tests for top/side changes and fallback stability.
- [ ] Run real default/alternate-pack inventory GL smoke and capture exact
  screenshot paths before committing.

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
