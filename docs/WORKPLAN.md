# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (streaming diagnostics) — after completing bounded
distance/visibility/collision priority, expose the still-hidden relight queue so
the next bottleneck decision is based on actual runtime evidence.

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

### Phase N7: Relight Queue Diagnostics

Promoted slice: relight-queue visibility split out of `PERF-B002`; this active
scope was removed from that backlog entry in the same transition.

Цель: expose pending bounded relight work through the existing immutable runtime
diagnostics snapshot and F3 HUD without adding per-frame filesystem reads or
reaching from HUD code into renderer internals.

- [ ] Add pending relight count to `RenderQueueSnapshot` at the existing
  renderer-to-HUD boundary and render it in the F3 queue line.
- [ ] Cover default/explicit snapshot values and HUD text without constructing
  `GameWindow` or a real GL scene in unit tests.
- [ ] Run the focused/full gates and a visible F3/F2 pass that creates or drains
  relight work, then move N7 into CHANGELOG.

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
