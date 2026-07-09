# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Phase G material metadata/atlas/snapshot foundation
продолжать Minecraft-like visual/resource-pack polish через opt-in
Iris/PBR-like material consumers, не включая дорогие эффекты по умолчанию и не
возвращая логику в `GameWindow` или `DemoWorldRenderer`.

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

### Phase G: Iris/PBR-Like Material Pipeline Foundation

Promoted backlog: `R-B007`.

Цель: продолжить shader/material pipeline foundation для future Iris/PBR-like
resource-pack support без включения дорогих эффектов по умолчанию.

### Phase G25: Material-Preview End-To-End Real-Scene Verification

- [ ] Run a hidden-window real scene with `material_quality = "material-preview"`
  to prove opt-in activation, atlas textures, and sampler binds work end-to-end
  against a real GL context without crashing or changing default rendering.
- [ ] Capture a material-preview screenshot plus the default-profile gameplay
  smoke screenshot and compare that default output is unchanged.
- [ ] Record any discovered material-preview defects in `docs/BUGS.md` and fix
  in-slice if small, otherwise file follow-up.
- [ ] Run focused shader/render tests, focused Pyright, unit gate before
  committing the slice.

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
