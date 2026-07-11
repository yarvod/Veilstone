# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (streaming priority) — bounded relight/remesh work now
prefers near-camera chunks; the next small slice adds camera-visible priority
without conflating it with the separate collision-critical future remainder.

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

### Phase N5: Camera-Visible Streaming Queue Priority

Promoted slice: `PERF-B003`.

Цель: among queued work at comparable distance, camera-visible chunks win over
off-screen chunks using a renderer-facing visibility snapshot or narrow score;
collision-critical priority remains future backlog scope.

- [ ] Identify the narrowest existing frustum/camera snapshot that can rank chunk
  or section keys without making the queue helper depend on OpenGL objects.
- [ ] Compose visibility with existing distance priority while preserving budget,
  FIFO ties, and deterministic behavior when visibility data is unavailable.
- [ ] Add pure order tests plus world-scene integration coverage for visible vs
  off-screen work at equal distance.
- [ ] Repeat RD3/RD4 frame-streaming and visible turn/walk/F3 acceptance, inspect
  F2 evidence, then move the completed slice into CHANGELOG.

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
