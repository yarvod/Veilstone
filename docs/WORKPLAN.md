# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (practical F3 diagnostics) — player input regressions are
closed with repeatable visible coverage; the next small slice makes location and
facing diagnosable directly in the running game.

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

### Phase N1: F3 Facing And Chunk Coordinates

Promoted slice: `DX-B001`.

Цель: extend the cached, renderer-agnostic F3 debug snapshot with Minecraft-like
block coordinates, chunk coordinates, and cardinal facing so world-streaming,
spawn, and navigation issues can be reported precisely without adding expensive
filesystem/device reads to the per-frame path.

- [ ] Audit the existing cached HUD/debug snapshot boundary and derive block,
  chunk, and facing values outside draw-only presentation code.
- [ ] Add deterministic unit coverage for negative coordinates, chunk boundaries,
  and cardinal direction transitions.
- [ ] Render compact F3 lines without growing `GameWindow` ownership or adding
  per-frame system queries.
- [ ] Launch the visible game, walk and turn across representative headings,
  confirm F3 values change correctly, capture through F2, and inspect the frame.

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
