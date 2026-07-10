# Veilstone — Рабочий План

## Overview

Активная цель: Phase L (reference gameplay verification, `WORLD-B004`) —
inventory interaction evidence is now reproducible; next work turns the
existing pure reference-scene fixture into a narrow real render capture.

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

### Phase L2: Rendered Reference Scene Foundation

Promoted from `WORLD-B004` and `DX-B002`; their active entries were removed from
`docs/BACKLOG.md` when this phase entered the workplan.

Цель: render the existing pure `reference_gameplay_scene` block fixture from a
known isometric camera through a fresh hidden runtime, producing one stable
numeric sidecar and a normal screenshot without moving scene ownership into
`GameWindow`.

- [ ] Add a narrow screenshot adapter/CLI around `reference_gameplay_scene`;
  keep its pure fixture and summary builders renderer-independent.
- [ ] Apply the fixture blocks to a temporary authoritative world and position a
  deterministic isometric camera without adding state to `GameWindow`.
- [ ] Validate block/camera/mesh numeric metadata, capture through
  `GameWindow.save_screenshot()`, and return an explicit display-less skip.
- [ ] Add focused unit tests and run a real visible-game/OpenGL capture when
  available, including visual inspection of the saved screenshot.

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
