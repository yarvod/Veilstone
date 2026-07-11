# Veilstone — Рабочий План

## Overview

Активная цель: Phase N (planning truth) — swimming feedback and render-test
isolation are complete; the next small slice removes completed/stale entries
from BACKLOG so future promotion cannot accidentally repeat finished work.

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

### Phase N3: Backlog Truth Audit

Scope: `docs/BACKLOG.md` status/history cleanup.

Цель: BACKLOG contains only genuinely future/open work. Entries already marked
`fixed` or `done`, or proven implemented by current code plus CHANGELOG/history,
are removed rather than promoted again; historical results remain in CHANGELOG.

- [ ] Remove every explicitly `fixed`/`done` backlog entry after confirming its
  result is already represented in CHANGELOG or current code/tests.
- [ ] Audit remaining `open` entries for obvious implementation/history
  contradictions; remove only those proven complete, not merely partially done.
- [ ] Keep broad open items split into real future remainder without copying any
  active scope back into BACKLOG.
- [ ] Record the cleanup count in CHANGELOG, replace this completed phase with
  the next verified active slice, and commit the docs-only audit separately.

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
