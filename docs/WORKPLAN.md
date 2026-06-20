# Veilstone — Рабочий План

## Overview

Текущая цель: стабилизировать архитектуру Veilstone перед следующими крупными gameplay-направлениями: player feel, вода, Twilight Forest-like генерация, 3D player, UI polish, мобы, network и resource packs.

Этот файл хранит только активный план и ближайшие решения. Выполненная история живёт в `docs/CHANGELOG.md`; актуальные баги и quality debt — в `docs/BUGS.md`.

## Current Phase

### Phase A: Architecture Stabilization

Цель Phase A — убрать `GameWindow`/god-object/service-locator проблему маленькими PR/commits, сохраняя рабочее состояние после каждого шага.

Правила Phase A:

- Не делать большой переписывающий PR.
- Не добавлять Dishka сейчас; сначала manual composition root.
- Новые use cases/controllers не принимают `GameWindow` целиком.
- `DemoWorldRenderer` постепенно теряет владение storage/generation/streaming/fluid/registry/texture-pack loading.
- Архитектурные ограничения проверяются через `uv run lint-imports`.
- Перед закрытием шага обновлять `WORKPLAN`, `BUGS`, `CHANGELOG` согласно `CLAUDE.md`.

## Deliverables

- [x] A1 Architecture map/docs: `docs/ARCHITECTURE.md` описывает текущую карту, целевые слои, direction of knowledge, lifetimes, composition root, ports/adapters, GameWindow migration, Controller(GameWindow) migration и DemoWorldRenderer split.
- [x] A2 Import-linter setup: добавлен первый реалистичный контракт в `pyproject.toml`; команда `uv run lint-imports`.
- [x] A3 Composition root skeleton: добавлен `src/voxel_sandbox/app/composition.py` с `AppRuntime` и `WorldRuntime`, без изменения runtime behavior.
- [ ] A4 AppRuntime extraction: перенести app-level зависимости из `GameWindow`/entrypoints в ручную композицию: settings, paths, event bus, audio, content registries, texture pack service, settings store.
  - [x] A4.1 Add `build_app_runtime()` factory for settings, data root, event bus, audio bus/director, item registry, and settings store without changing runtime behavior.
  - [x] A4.2 Introduce the first compatibility path for passing `AppRuntime` toward `GameWindow`.
  - [x] A4.3 Move existing `GameWindow` app-level construction calls for data root, audio, event bus, and item registry to the runtime path.
  - [ ] A4.4 Extract texture pack service ownership; likely finish together with A7 `ApplyResourcePackUseCase`.
- [ ] A5 WorldRuntime extraction: перенести world-level зависимости: active world storage, block registry, generation/streaming, player state, entity world, simulation systems, renderer facade/port.
  - [x] A5.1 Add `build_world_runtime()` and attach `GameWindow.world_runtime` as an explicit map of current active-world dependencies without changing runtime behavior.
  - [x] A5.2 Move player/entity simulation construction behind `build_local_world_runtime()` while preserving `GameWindow.player` and `GameWindow.entities` compatibility fields.
  - [x] A5.3 Refresh `world_runtime` during world switching so compatibility fields stay synchronized after renderer/player/entity replacement.
  - [ ] A5.4 Keep compatibility fields until controllers/renderers are migrated.
- [ ] A6 Replace one controller from `Controller(GameWindow)` to explicit dependencies. Начать с самого узкого участка, сохранить compatibility adapter при необходимости.
  - [x] A6.1 Narrow `HudController` from nominal `GameWindow` type to explicit `HudView` Protocol listing the HUD-facing surface.
  - [x] A6.2 Replace `HudController(self)` with `HudController(HudWindowAdapter(self))`, localizing the window compatibility adapter.
  - [x] A6.3 Move HUD frame/layout reads (`width`, `height`, `inventory_open`) to `HudFrameSnapshot` view data.
  - [ ] A6.4 Continue replacing HUD direct adapter reads with snapshots where useful.
- [x] A7 Extract `ApplyResourcePackUseCase`: единая логика для UI и `/resourcepack`; зависимости: texture pack service, world render port, settings store.
  - [x] A7.1 Add `application.resource_packs.ApplyResourcePackUseCase` with `WorldRenderPort`, `SettingsStorePort`, injected atlas loader, and unit tests.
  - [x] A7.2 Route `/resourcepack` command through `ApplyResourcePackUseCase`.
  - [x] A7.3 Route Settings Texture Packs UI through the same use case.
  - [x] A7.4 Move texture pack discovery/loading/cache ownership behind a service port.
- [ ] A8 Split renderer/world ownership boundaries gradually: storage/generator/streamer/fluid/lighting/registry уходят в runtime/simulation; renderer остаётся GPU scene adapter.
- [ ] A9 Add isolated tests for use cases/systems: resource pack apply, player movement, fluid step, mob spawning, generation pipeline без Pyglet/OpenGL.

## Immediate Next Step

Последний завершённый шаг: A8.8 moved `InputHandler` mining fluid checks from direct renderer registry to `world_runtime.block_registry`.

Следующий кодовый шаг: continue A8 renderer/world ownership boundary split.

1. Move the next small world lifecycle caller from direct renderer fields toward `WorldRuntime`/ports.
2. Keep draw behavior unchanged; do not split the renderer class wholesale yet.
3. Keep command and UI resource pack behavior covered by use case tests.
4. Проверить `uv run lint-imports`, `uv run ruff check .`, `uv run ruff format --check .`, focused tests.

## Architecture Guardrails

Enforced now:

- `voxel_sandbox.domain` must not import `app`, `audio`, `infrastructure`, `network`, or `render`.
- `voxel_sandbox.engine` must not import `render`.
- `voxel_sandbox.application` must not import Pyglet or ModernGL.

Staged next:

- Presentation may import application; application must not import presentation.
- Domain/simulation must not import infrastructure directly except through composition/adapters.

## Phase A Acceptance

- `GameWindow` migration strategy documented.
- `Controller(GameWindow)` migration strategy documented.
- `DemoWorldRenderer` responsibility split documented.
- `import-linter` configured and runnable through `uv run lint-imports`.
- At least one dependency rule enforced.
- No Dishka introduced.
- Existing runtime behavior unchanged by A1-A3.

## Future Gameplay Acceptance

After Phase A, these must become practical:

- New gameplay systems can be tested without Pyglet window or OpenGL context.
- Controllers no longer receive full `GameWindow`.
- Simulation systems do not import render/window/UI.
- Renderer does not own world persistence/generation.
- Resource pack application exists as an application use case.
- Water movement, mob spawning, world generation and player movement can each be tested independently.
