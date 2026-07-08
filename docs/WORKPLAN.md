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

Promoted backlog: `R-B005`.

Цель: продолжить terrain visual polish через render-only vegetation motion без
накопления нового долга в `GameWindow`.

### Phase E3: Render-Only Vegetation Motion

- [x] Define render-facing vegetation wind data grass/leaves/plants that
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
