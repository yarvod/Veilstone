# Veilstone — Рабочий План

## Overview

Активная цель: Phase K (inventory/crafting polish, `BUG-G006`) — both drag
distribution gestures are complete; next work fixes the concrete action-status
priority regression exposed by the K6 smoke.

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

### Phase K7: Inventory Action Feedback Priority

Tracked issue: `BUG-G006`.

Цель: fresh inventory actions such as `Distributed`, `Moved`, and `Crafted`
remain visible instead of being immediately masked by derived recipe feedback
such as `No matching recipe`.

- [ ] Extract a pure presentation resolver for action status versus crafting
  result feedback without adding conditionals to `draw_inventory()`.
- [ ] Preserve recipe availability/error feedback when no fresh action message
  exists, while keeping explicit action messages readable.
- [ ] Add focused presentation tests for action, recipe error, available result,
  and default instruction states.
- [ ] Re-run the mixed-capacity K6 GL scene and capture visible action feedback.

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
