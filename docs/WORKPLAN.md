# Veilstone — Рабочий План

## Overview

Активная цель: после закрытия Phase D architecture cleanup и grass/terrain
material coherence продолжать Minecraft-like visual/resource-pack polish через
render-only vegetation motion, не возвращая логику в `GameWindow` или
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

### Phase G: Iris/PBR-Like Material Pipeline Foundation

Promoted backlog: `R-B007`.

Цель: продолжить shader/material pipeline foundation для future Iris/PBR-like
resource-pack support без включения дорогих эффектов по умолчанию.

### Phase G6: Resource-Pack Material Bundle Assembly

- [ ] Add importer-level helper that assembles a CPU material atlas bundle from
  a loaded color atlas and Java-style sidecar tile maps.
- [ ] Build deterministic fixture coverage proving fixture packs produce bundle
  roles only when matching sidecars exist.
- [ ] Keep low-tier runtime unchanged: no additional shader uniforms/textures are
  required unless a later quality tier enables them.
- [ ] Run real-game smoke to confirm unchanged-color rendering path.

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
