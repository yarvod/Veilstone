# Veilstone — Рабочий План

## Overview

Активная цель: довести gameplay prototype до более Minecraft-like ощущения,
не ломая архитектурные границы из `docs/ARCHITECTURE.md`.

Важное уточнение: Phase B1/B2/B4 закрыли MVP-срезы, но не финальное качество.
Текущая задача — связать игрока, камеру, звук, анимации, воду, UI, генерацию и
мультиплеер в цельное ощущение игры, а не просто добавлять изолированные фичи.

Выполненная история живёт в `docs/CHANGELOG.md`; актуальные баги и quality debt —
в `docs/BUGS.md`.

## Product Direction

Игрок должен ощущаться настоящей сущностью в мире:

- в первом лице видна 3D-рука и предмет/блок в руке;
- при ходьбе/спринте камера, шаги, рука и тело используют один ритм движения;
- при атаке, ломании и постановке блоков есть swing-анимации;
- в третьем лице локальный игрок видит себя как полноценного персонажа;
- в мультиплеере другие игроки видны как такие же сущности, с интерполяцией,
  анимациями, тенью, предметом в руке и ником над головой.

## Architecture Direction For Phase C

Новые player/mob/UI/render фичи нельзя добавлять напрямую в `GameWindow` как
новые куски состояния. Нужны компактные слои данных:

- simulation/engine считает состояние игрока, мобов, воды и взаимодействий;
- application готовит render/network snapshots без Pyglet/OpenGL;
- render только рисует snapshots и отдаёт input/use-case команды;
- network реплицирует компактные player/entity states, а не renderer objects;
- audio получает события из gameplay/animation state, а не живёт отдельным
  таймером внутри окна.

Полноценный DI-контейнер пока не обязателен. Сначала усиливаем ручную
composition root, ports, factories и narrow dependencies. Возвращаться к Dishka
стоит только когда ручная сборка станет реально шумной и стабильные границы уже
будут понятны.

## Input / F-key Policy

F-клавиши должны быть player-facing управлением, а не случайной панелью
графических настроек.

- Графические настройки (`smooth lighting`, AO, fog, shadows, clouds, render
  distance, postprocess) должны управляться из Settings UI и сохраняться в
  settings.
- F-клавиши можно использовать для Minecraft-like действий:
  - perspective cycle;
  - debug overlay;
  - hide HUD;
  - screenshot;
  - dev-only tools, если они явно помечены как development/debug.
- Текущие F6/F7/F8/F9 toggles для lighting/AO/fog/meshing нужно мигрировать в
  Settings UI или debug/dev submenu, чтобы освободить понятную схему управления.
- Если `F5` используется для perspective cycle, shader reload должен переехать в
  dev menu, command, или другой явно development-only binding.

## Current Phase

### Phase C: Minecraft-like Gameplay Feel & Presentation

### Phase C1: Player embodiment / first-person viewmodel

Цель: игрок в первом лице должен иметь тело/руку/предмет, а не быть камерой,
которая летает по миру.

- [x] Add deterministic `PlayerAnimationState` / gait state in engine or
      application-facing data: movement phase, walk/sprint cadence, grounded
      state, swim state, jump/fall state, interaction state, selected hand.
- [x] Move footstep timing out of the ad-hoc render-window accumulator so gait
      phase is the single source of truth for steps.
- [x] Drive camera bob from the same gait phase; walking and sprinting should
      feel different but synchronized with footsteps.
- [x] Add first-person 3D hand/viewmodel renderer that consumes a snapshot, not
      raw `GameWindow` state.
- [x] Add application-level first-person viewmodel pose snapshot for hand,
      held item, bob, and swing animation data.
- [x] Add render-facing first-person viewmodel part data for hand and held item.
- [x] Render selected held item/block as a first 3D cuboid MVP in the hand.
- [x] Add attack/break/place swing animation with clear start, progress, finish,
      and cancellation behavior.
- [ ] Add block breaking feedback hook so hand animation, sound, particles later
      can share the same interaction event.
- [ ] Add local player shadow path where render quality allows it.
- [x] Add tests for gait phase, interaction state transitions, and snapshot
      generation without Pyglet/OpenGL.

### Phase C2: Networked player entity and third-person camera

Цель: локальный игрок и remote players должны использовать одну модель игрока,
одну систему анимации и один render pipeline. Это ключевая база для
мультиплеера.

- [ ] Define first-class player entity render snapshot:
      position/orientation, body pose, head yaw/pitch, limb animation phase,
      held item, name, health/status flags where needed.
- [ ] Make local third-person player rendering use the same player snapshot path
      as remote players.
- [x] Add render-layer held item/block cuboid support for player avatar entities.
- [x] Add camera perspective modes: first person, third-person back,
      third-person front.
- [x] Add Minecraft-like perspective cycle binding after resolving current F-key
      conflicts.
- [ ] Add remote player interpolation so multiplayer movement does not jitter.
- [ ] Render remote player nameplates above head with distance/readability rules.
- [x] Add nameplate snapshot/render data with distance fade visibility rules.
- [x] Render held item/block for remote players.
- [ ] Render player shadow for local third-person and remote players.
- [x] Keep networking payload compact: replicate entity/player state, not render
  objects.
- [x] Add tests for player snapshot mapping and remote held-item payload without
  Pyglet/OpenGL.

### Phase C3: Audio feel pass

Цель: шаги должны быть тише, приятнее и синхронны с движением.

- [x] Lower default footstep/block-step audio gains in `config/audio.toml`.
- [x] Split block action sounds from walking sounds where needed so breaking,
      placing, and walking can be tuned independently.
- [x] Sync footstep events to gait phase instead of a separate render-window
      accumulator.
- [x] Add per-material step sound tuning with sane default gain ranges.
- [x] Add walk/sprint cadence tests.
- [ ] Later: add landing, swimming, splash, and block interaction sounds through
      gameplay events, not direct renderer calls.

### Phase C4: Water playability and rendering

Цель: вода должна быть играбельной сейчас и визуально приятнее потом.

- [x] Fix player inability to reliably climb from water onto shore.
- [x] Add regression test for water-to-land movement at shore blocks.
- [ ] Verify swimming, buoyancy, jump/step-up, and collision rules do not fight
      each other near shore blocks.
- [ ] Smooth visible water flow transitions after block breaks.
- [ ] Keep near-term simulation Minecraft-like voxel water: sources, flow,
      levels, chunk boundaries.
- [ ] Treat smooth continuous water, waves, ripples, splashes, and player
      surface disturbance as later renderer effects over voxel simulation.
- [ ] Add debug visualization or tests for fluid levels/dirty propagation before
      adding expensive visual smoothing.

### Phase C5: Mobs locomotion pass

Цель: коровы/зомби не должны скользить как манекены; ноги должны соответствовать
реальному движению.

- [ ] Replace one-loop walk animation with locomotion-driven animation phase.
- [ ] Sync cow/zombie leg movement to actual velocity and ground contact.
- [ ] Add idle, walk, turn, hurt/death animation state separation.
- [ ] Avoid sliding/ice-skating when mobs slow down, turn, or hit obstacles.
- [ ] Sync future mob footstep sounds to animation contact phase.
- [ ] Add focused tests for animation phase advancement from entity velocity.

### Phase C6: Texture transparency and resource-pack correctness

Цель: листья и похожие блоки должны иметь прозрачные участки, как в Minecraft
resource packs.

- [x] Add alpha-tested/cutout block rendering path for leaves and similar blocks.
- [x] Preserve depth behavior so leaf holes show the world through transparent
      texture regions without sorting artifacts.
- [x] Mark blocks/materials that require cutout rendering in data registry.
- [x] Verify Faithful-style leaf textures render with visible holes.
- [x] Document supported vs planned resource-pack features.
- [x] Add a smoke/manual test scene or fixture for transparent foliage.

### Phase C7: Inventory and item presentation

Цель: инвентарь должен быть функциональным и визуально похожим на Minecraft UX.

- [ ] Add render-facing item icon/model snapshots separate from inventory rules.
- [x] Show Minecraft-like stack count in the lower-right corner of item icons.
- [x] Show hover tooltip with item name.
- [x] Add drag-and-drop slot movement.
- [x] Add clear selected/hover visual states.
- [x] Add clear drag visual states.
- [ ] Improve crafting UX without coupling UI directly to domain internals.
- [ ] Later: 3D item/block icons in inventory once item model rendering exists.
- [ ] Keep inventory domain pure; UI should send commands/use cases, not mutate
      domain internals directly.

### Phase C8: World generation and distance

Цель: мир должен давать красивые дали и больше живого наполнения.

- [ ] Add Settings UI control for `[world].render_distance`.
- [ ] Persist render distance changes and rebuild/reconfigure chunk streaming
      safely.
- [ ] Improve distant landscape readability and biome silhouettes.
- [ ] Add more ground cover: grass, flowers, biome-specific small features.
- [ ] Add landmarks/points of interest that are visible at distance.
- [ ] Add tests for feature density ranges and generation determinism.
- [ ] Watch performance: higher render distance must not block render thread.

### Phase C9: Debug, HUD, screenshot, and perspective controls

Цель: сделать понятные Minecraft-like controls и убрать графические toggles из
обычных F-клавиш.

- [x] Add perspective cycling for first/third-person modes.
- [x] Add or reserve hide-HUD behavior.
- [x] Add or reserve screenshot behavior.
- [ ] Expand debug overlay with coordinates, FPS/frame timings, chunk/mesh
      counts, memory estimate, Python/runtime info, CPU/GPU device strings where
      available.
- [ ] Move lighting/AO/fog/meshing toggles to Settings UI or explicit dev menu.
- [x] Remove player-facing dependence on F6/F7/F8/F9 for graphics settings once
      Settings UI equivalents exist.
- [ ] Keep expensive system telemetry out of per-frame hot paths; cache or
      update slow diagnostics at low frequency.

### Phase C10: Time-of-day polish

Цель: время суток должно ощущаться как Minecraft-like day/night cycle, а команды
должны быть понятными.

- [x] Make default full day/night cycle 20 minutes (`1200` seconds).
- [x] Make `/time set day` mean beginning of day/sunrise, not noon.
- [ ] Tune dawn/day/sunset/night proportions toward Minecraft-like feel.
- [ ] Add explicit dawn/sunset transition tuning rather than only one linear
      full-cycle value if renderer needs it.
- [ ] Expose/finalize named time semantics in command tests and README.

## Completed MVP Phases

### Phase B1: Player Feel — MVP DONE

Done: coyote time, jump buffering, variable jump height, sprint, head bob.

Remaining quality work moved to Phase C1/C3.

### Phase B2: Water — MVP DONE

Done: cross-chunk water flow, infinite source creation, ticking loaded chunks each
fluid step, dirty neighbor propagation.

Remaining playability/rendering work moved to Phase C4.

### Phase B3: Twilight-like Generation — MVP DONE

- [x] Add biome-sensitive hill amplitude and stronger Twilight biome silhouettes.
- [x] Add dungeon chamber decorator isolated generation test.
- [x] Add Dusk Highlands pillar/ore-cap decorator isolated generation test.
- [x] Add small structure/feature variety pass for Twilight Woods/Gloom Swamp.
- [x] Add deterministic tests for new generation rules/render integration.
- [x] Review densities and block IDs against data registries before wider tuning.

Remaining richness/distance work moved to Phase C8.

### Phase B4: 3D Player Model — MVP DONE

- [x] Add `PlayerRenderSnapshot` application view data without Pyglet/ModernGL.
- [x] Add render adapter that can consume `PlayerRenderSnapshot`.
- [x] Add first local/third-person player model draw path behind settings/debug
      toggle.

Remaining embodiment/viewmodel/networked-player work moved to Phase C1/C2.

## Check Gate

Run before commits:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pyright
```

`pyright` currently expected fail only known BUG-Q001 baseline.
