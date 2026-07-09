# Veilstone — Рабочий План

## Overview

Активная цель: Phase G (Iris/PBR-like material pipeline, `R-B007`) закрыта —
opt-in `material-preview` профиль рисует чанки material-шейдером с
NORMAL/SPECULAR атласами, переключается через `/materials` и Settings UI, а
default/low остаются color-only. Следующая цель — Phase H: scalable visual
quality tiers (`R-B008`), не возвращая логику в `GameWindow` или
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

### Phase H: Scalable Visual Quality Tiers

Promoted backlog: `R-B008`.

Цель: явные пресеты качества (`low_60`, `balanced`, `high`, `cinematic`),
резолвящиеся в один `RenderQualityProfile`, вместо рассыпанных независимых
graphics-флагов.

### Phase H2: Apply Resolved Preset At Renderer Construction

- [ ] When `graphics.quality_preset != "custom"`, resolve the profile and use
  its knobs when constructing `DemoWorldRenderer` (shadow quality, AO, smooth
  lighting, fog, clouds, vegetation wind, material quality, optional render
  distance override).
- [ ] Keep `custom` on the existing per-flag path with zero behavior change.
- [ ] Unit tests for the settings→renderer knob mapping.
- [ ] Real smoke: launch with `low_60` and `high` presets, capture screenshots,
  verify F3 reflects the profile; default smoke unchanged.

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
