# Veilstone — Рабочий План

## Overview

Активная цель: Phase J (water surface visual quality, `R-B009`) — crest
highlights, quality-profile gating, and procedural ripple reflections are
implemented and smoke-tested; next work should make water visual/physics smoke
evidence reproducible without mixing simulation fixes into render/UI classes.

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

### Phase J4: Reproducible Water Surface Smoke

Promoted backlog: `R-B009`.

Цель: replace one-off water screenshot scripts with a deterministic smoke tool
that captures visual quality tiers and stable item buoyancy from `BUG-G008`.

- [ ] Add a reusable water-surface smoke command/tool with a deterministic
  camera and visible water scene.
- [ ] Capture `low_60` and detailed-profile screenshots plus resolved
  `water_detail` state in machine-readable metadata.
- [ ] Include floating-item height/velocity/jitter metrics without coupling the
  smoke tool to render internals beyond the existing window/runtime adapters.
- [ ] Run the smoke on a real GL context and document exact output paths before
  committing.

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
