# Veilstone — Рабочий План

## Overview

Активная цель: Phase M (player input stability) — rendered reference-scene
capture is complete; next work reproduces and removes the reported intermittent
stuck movement state before expanding other gameplay polish.

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

### Phase M1: Stuck Movement Key Lifecycle

Tracked bug: `BUG-I001`.

Цель: deterministically reproduce and eliminate any movement state that remains
active after key release or gameplay focus transitions, without hiding the
problem behind per-frame polling or broad input rewrites.

- [ ] Audit `KeyState`, Pyglet key press/release, focus deactivate/activate,
  inventory, pause, and Resume transitions; add deterministic failing coverage
  for any stale movement path found.
- [ ] Apply the smallest lifecycle fix at the input boundary and keep gameplay
  movement rules independent from presentation/window state.
- [ ] Add a repeatable visible-game sequence for walk/sprint release, focus
  change, inventory, and repeated Escape/Resume; record numeric post-release
  drift and exact interaction results.
- [ ] Capture and visually inspect an F2 frame after the sequence, while treating
  the screenshot as supplemental evidence rather than proof of key behavior.

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
