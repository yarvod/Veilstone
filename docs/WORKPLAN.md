# Veilstone — Рабочий План

## Overview

Активная цель: продолжать gameplay-развитие после Phase A architecture stabilization, сохраняя правила из `docs/ARCHITECTURE.md`: новые системы тестируются без Pyglet/OpenGL, presentation вызывает application/runtime ports, renderer не владеет gameplay state.

Выполненная история живёт в `docs/CHANGELOG.md`; актуальные баги и quality debt — в `docs/BUGS.md`.

## Current Phase

### Phase B: Gameplay Improvements

#### Phase B1: Player Feel — DONE

Сделано: coyote time, jump buffering, variable jump height, sprint, head bob.

#### Phase B2: Water — DONE

Сделано: cross-chunk water flow, infinite source creation, тик всех загруженных чанков за fluid step, dirty neighbor propagation.

#### Phase B3: Twilight-like Generation — DONE

- [x] Add biome-sensitive hill amplitude for stronger Twilight biome silhouettes.
- [x] Add dungeon chamber decorator and isolated generation test.
- [x] Add Dusk Highlands pillar/ore-cap decorator and isolated generation test.
- [x] Add small structure/feature variety pass for Twilight Woods and Gloom Swamp.
- [x] Add deterministic tests for any new generation rule before render integration.
- [x] Review densities and block IDs against data registries before wider tuning.

#### Phase B4: 3D Player Model — ACTIVE

- [x] Add `PlayerRenderSnapshot` application view data without Pyglet/ModernGL.
- [x] Add render adapter that can consume `PlayerRenderSnapshot`.
- [ ] Add first local/third-person player model draw path behind settings or debug toggle.

## Next Phases

- [ ] Phase B5: UI polish; keep UI invoking use cases/runtime ports, not renderer internals.
- [ ] Phase B6: Mobs; spawning and AI tested through `WorldQuery`/`EntityWorld` without GPU.
- [ ] Phase B7: Network polish; persistence/session changes through runtime/application boundaries.
- [ ] Phase B8: Resource packs polish; all apply/reload paths use `ApplyResourcePackUseCase`.

## Architecture Baseline

Phase A is closed for planning purposes. Keep these rules active:

- No Dishka until manual composition becomes repetitive enough to justify it.
- New controllers/use cases do not accept full `GameWindow`.
- `DemoWorldRenderer` remains GPU scene adapter; world ownership stays in runtime/composition.
- `uv run lint-imports` must stay green.
- `pyright` remains known quality debt tracked in `docs/BUGS.md`; do not add new typing debt when touching files.

## Check Gate

Run before commits:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pyright
```

`pyright` is currently expected to fail only with the known BUG-Q001 baseline.
