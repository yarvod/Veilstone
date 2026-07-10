# Veilstone — Рабочий План

## Overview

Активная цель: Phase M (player input stability) — movement, pause/Resume,
inventory, and focus key lifecycles now have repeatable visible coverage; next
work isolates the reported fresh-launch first-click/double-click regression.

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

### Phase M2: Fresh-Launch First-Click Reliability

Tracked bug: `BUG-I002`.

Цель: ensure the first ordinary mouse click after a fresh visible launch or
window activation reaches exactly one intended UI action regardless of initial
pointer movement, without adding double-click workarounds or duplicate dispatch.

- [ ] Audit Cocoa/Pyglet activate/deactivate ordering, widget hover/pressed state,
  and menu mouse press/release dispatch during cold start and focus regain.
- [ ] Add deterministic regression coverage for the exact lost-first-click or
  duplicate-dispatch path found; do not add timing/debounce guesses.
- [ ] Apply the smallest focus/event-routing fix and preserve one action per
  single click across main, world-list, Settings, and pause menus.
- [ ] Run repeated visible cold launches with and without initial pointer motion,
  record first-click action counts, and visually inspect representative menu and
  in-game F2 frames.

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
