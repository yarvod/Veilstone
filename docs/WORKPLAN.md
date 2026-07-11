# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (quality isolation) — swimming feedback is complete with
real input/audio/render evidence; the next small slice removes the confirmed
order-dependent Pyglet context failure from the render test group.

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

### Phase N2: Pyglet UI Renderer Test Isolation

Tracked bug: `BUG-T001`.

Цель: `tests/unit/render/test_ui_renderer.py` passes both alone and after the
preceding render tests by owning a valid shader-capable Pyglet context for its
actual lifetime, without hiding failures behind skips or changing production UI
behavior.

- [ ] Identify which preceding test/module closes or replaces the shared Pyglet
  context and reproduce the shortest deterministic order.
- [ ] Give UI renderer tests explicit context setup/teardown ownership using the
  existing GL test support; do not rely on import-time shadow-window accidents.
- [ ] Prove the isolated file, shortest reproducer, full `tests/unit/render`, and
  full unit gate all pass without new skips.
- [ ] Mark `BUG-T001` fixed with the exact reproducer and final counts, then move
  this phase out of WORKPLAN into CHANGELOG.

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
