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

### Phase H1: RenderQualityProfile Resolution

- [ ] Add a render-facing `RenderQualityProfile` dataclass resolving a preset
  name into concrete knobs (render distance, shadow quality, AO, smooth
  lighting, fog, clouds, vegetation wind, material quality).
- [ ] Add `graphics.quality_preset` setting (default `custom`) that, when not
  `custom`, resolves the profile; `custom` keeps current individual flags.
- [ ] Keep behavior change zero for existing settings files (they resolve to
  `custom`).
- [ ] Unit tests for preset resolution and custom passthrough.
- [ ] Focused Pyright + unit gate + default gameplay smoke screenshot before
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
