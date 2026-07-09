# Veilstone — Рабочий План

## Overview

Активная цель: Phase I (shadow artifact cleanup after quality tiers) —
medium/high shadow captures now reproduce the hard terrain artifacts from
`BUG-R006`, while `off` stays clean. Следующий шаг — fix the receiver/shadow
math without folding logic back into `GameWindow` or `DemoWorldRenderer`.

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

### Phase I3: Shadow Artifact Fix

Promoted bug: `BUG-R006`.

Цель: убрать hard triangular/blocky terrain shadow artifacts from the receiver
path while keeping `off` preset clean and preserving material-preview lighting.

- [ ] Inspect shadow receiver sampling in `chunk_opaque.frag` and
  `chunk_material_preview.frag` against the `off`/`medium`/`high` captures.
- [ ] Verify whether projected coordinates, depth compare, bias/filtering, or
  shadow matrix bounds cause the broad dark triangles.
- [ ] Add focused shader/math coverage where practical, or a deterministic
  smoke assertion around shadow preset metadata if shader-level unit coverage is
  not feasible.
- [ ] Run `shadow-preset-smoke` again and compare screenshots before/after.

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
