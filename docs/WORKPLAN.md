# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Minecraft-like gameplay-feel Phase C стабилизировать
архитектуру, чтобы следующие визуальные, аудио, inventory и resource-pack фичи не
наращивали `GameWindow` и `DemoWorldRenderer` как супер-классы.

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
- real-game smoke checks обязательны для UI/render/audio/controls changes;
- focused Pyright обязателен для затронутых typed boundaries; full Pyright пока
  tracked как known-red `BUG-Q001`.

## Current Phase

### Phase D: Architecture Cleanup And Runtime Diagnostics

Цель: раздербанить оставшиеся странные зависимости вокруг `GameWindow`,
`DemoWorldRenderer` и chunk/runtime orchestration, сохранив игру runnable после
каждого маленького среза.

Promoted backlog: `ARCH-B001`, `PERF-B002`, `PERF-B003`, `R-B006`,
`WORLD-B004`, `DX-B002`.

### Phase D1: Controller Ports Instead Of Full GameWindow

- [x] Map remaining controllers/use cases that still receive full `GameWindow` (`GameplayController`, `InventoryController`, `NetworkController`; HUD already uses an adapter).
- [x] Route `GameplayController` through `GameplayView`/`GameplayWindowAdapter`
      instead of passing the full `GameWindow` object.
- [x] Route `InventoryController` through `InventoryView`/`InventoryWindowAdapter`
      instead of passing the full `GameWindow` object.
- [x] Route `NetworkController` through `NetworkView`/`NetworkWindowAdapter`
      instead of passing the full `GameWindow` object.
- [x] Route `InputHandler` through `InputView`/`InputWindowAdapter` with
      inventory and network input ports instead of private `GameWindow` members.
- [ ] Shrink `GameplayView`/`InventoryView`/`NetworkView`/`InputView` toward
      narrower command, UI, and session ports instead of broad window-adapter
      surfaces.
- [ ] Extract remaining HUD/debug snapshot reads so HUD code does not depend on
      broad window state; inventory draw now goes through `InventoryHudPort`.
- [ ] Keep `/resourcepack`, F-key controls, inventory, and debug overlay smoke
      tested through real app paths after each controller slice.
- [ ] Update `docs/ARCHITECTURE.md` and `docs/BUGS.md` watchlist as each window
      dependency is removed.

### Phase D2: Chunk Runtime Pipeline And Perf Snapshots

- [ ] Move chunk streaming/relight/remesh scheduling policy behind a runtime or
      render-pipeline helper instead of adding more orchestration to
      `DemoWorldRenderer`.
- [ ] Add `RuntimePerfSnapshot` or equivalent application/render-facing data for
      frame/update/render timings, chunk queues, mesh queues, and visible chunks.
- [ ] Feed F3/debug overlay from cached perf snapshots without expensive
      per-frame telemetry reads.
- [ ] Add focused tests for scheduling priority/budgets without constructing
      Pyglet or ModernGL.
- [ ] Keep `benchmark-frame-streaming --render-distance 3/4` as the real hidden
      window performance smoke for this phase.

### Phase D3: Block/Item Model Snapshot Layer

- [ ] Define render-facing block/item model snapshot data for chunk blocks,
      held items, dropped items, inventory icons, and remote held items.
- [ ] Route inventory 3D item/block icons through the snapshot layer instead of
      UI-local rendering rules.
- [ ] Keep resource-pack texture lookup Minecraft-like and folder-routable for
      default and user packs.
- [ ] Add unit coverage proving registry/resource-pack data maps to stable model
      snapshots without OpenGL.

### Phase D4: Reference Gameplay Snapshot Scenes

- [ ] Add deterministic debug scene fixtures for generation, water, foliage,
      lighting, mob movement, inventory icons, and first-person interaction.
- [ ] Add dev-only screenshot/isometric capture command with metadata sidecar
      seed, resource pack, render distance, and settings.
- [ ] Use numeric summaries first; promote visual golden checks only when output
      is stable enough not to churn.

## Check Gate

Run before commits unless a narrower WIP checkpoint is explicitly documented:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pyright
```

`pyright` currently expected to fail only known `BUG-Q001` baseline.
