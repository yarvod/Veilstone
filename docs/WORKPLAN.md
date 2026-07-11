# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (measured lighting optimization) — after reducing
propagation scratch churn, skip the still-measured block-light sweep when a
relight region contains no emitting source.

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

### Phase N12: Zero-Source Light Propagation Fast Path

Promoted slice: all-zero `_propagate_light` source fast path split out of
`PERF-B001`; this active scope was removed from that backlog entry in the same
transition.

Цель: return an independent zero light volume before allocating propagation
scratch arrays when a region has no sky/block emission, without weakening
emissive, removal, opaque, or cross-chunk behavior.

- [ ] Prove all-zero output, dtype, independent ownership, and no input mutation;
  preserve existing lantern/removal/cross-chunk tests.
- [ ] Add the zero-source guard before blocked/scratch allocation and retain the
  shared propagation path for any nonzero source.
- [ ] Compare zero-source microbenchmark and unprofiled RD3/RD4, then run a
  visible emissive/removal F2 pass before moving N12 into CHANGELOG.

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
