# Veilstone UI + Performance Upgrade Plan

Документ для Codex/AI-агента: улучшить визуал стартового интерфейса, экранов выбора режима/мира и поднять FPS без слома архитектуры.

Рекомендуемый путь в репозитории:

```text
docs/UPDATE_UI_PERFORMANCE_PLAN.md
```

## 1. Контекст

Veilstone — Python voxel sandbox engine prototype на Python 3.13, `pyglet`, `ModernGL`, `NumPy`, `uv`. В проекте уже есть меню, одиночка через локальный authoritative server/client transport, multiplayer, чанки, greedy meshing, вода, освещение, мобы, сохранения, бенчмарки и smoke/integration/unit тесты.

Текущая проблема:

```text
На железе уровня Intel i3-7100 / 16 GB RAM / Radeon RX550 4GB игра выдаёт около 20–30 FPS,
хотя Minecraft на этом же ПК держит около 60 FPS на заметно большей дальности.
```

Основные гипотезы:

```text
1. CPU-side overhead в Python важнее, чем GPU-тени.
2. UI/HUD рисуется слишком вручную и дорого.
3. Frustum culling создаёт лишние NumPy/Python-объекты на каждую секцию каждый кадр.
4. Render path делает streaming/update работу.
5. Singleplayer всегда поднимает локальный LAN-server + ClientSession.
6. Remesh/relight при изменениях слишком крупный.
7. ProcessPool может гонять слишком много мелких section-задач и массивов.
```

## 2. Главные цели

### 2.1 Визуал и интерфейс

Сделать интерфейс не “debug menu”, а игровой UI:

```text
- красивое стартовое меню;
- нормальные кнопки с hover/pressed/disabled состояниями;
- аккуратные панели;
- экран выбора мира с карточками миров;
- экран создания мира;
- настройки с понятными rows/toggles;
- единая тема Veilstone;
- mouse + keyboard navigation;
- меньше ручного позиционирования label-ов;
- меньше отдельных draw-вызовов.
```

### 2.2 Производительность

Сделать низкоуровневые оптимизации без смены движка:

```text
- удержать стабильные 60 FPS на low/potato preset при render_distance=2;
- уменьшить CPU overhead в кадре;
- уменьшить стоимость UI/HUD;
- вынести streaming/update работу из render path;
- ускорить culling;
- уменьшить лишний remesh/relight;
- подготовить движок к render_distance 4–8 как следующей цели.
```

### 2.3 Тестируемость

Все изменения должны проходить:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m smoke
```

Если изменение касается производительности, запускать релевантные бенчмарки:

```bash
uv run python -m voxel_sandbox benchmark-frame-streaming
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-streaming
```

## 3. Не цели

Не делать это в рамках текущего плана:

```text
- не мигрировать игру на PySide/PyQt;
- не мигрировать игру на pygame;
- не подключать тяжёлый desktop GUI toolkit внутрь игрового окна;
- не переписывать весь движок;
- не менять арт-стиль на чужой/Minecraft-like копию;
- не ломать существующие команды запуска;
- не удалять multiplayer ради FPS;
- не отключать тесты ради скорости разработки.
```

PySide/PyQt можно рассматривать только как отдельный внешний launcher/editor в будущем, но не как UI внутри ModernGL/pyglet окна.

## 4. Правила для Codex/AI-агента

### 4.1 Общие правила работы

Codex должен работать маленькими безопасными шагами.

Перед началом задачи:

```text
1. Прочитать этот документ.
2. Прочитать README.md.
3. Найти релевантные файлы.
4. Сформулировать краткий план.
5. Создать/обновить backlog-запись.
6. Не делать большой rewrite без метрик.
```

После выполнения задачи:

```text
1. Запустить ruff/pyright/pytest.
2. Запустить релевантный smoke/integration test.
3. Если задача performance-related — записать baseline и result.
4. Обновить backlog-запись.
5. Описать, какие файлы изменены и почему.
```

### 4.2 Запреты

Codex не должен:

```text
- делать огромный PR “улучшил всё”;
- менять архитектуру без тестов;
- заменять pyglet/ModernGL на другой стек;
- добавлять PySide/PyQt в runtime игры;
- добавлять нестабильные GUI-библиотеки без отдельного ADR;
- удалять существующие тесты;
- помечать задачу done без acceptance checks;
- скрывать падение тестов;
- оптимизировать вслепую без проверки FPS/бенчмарков.
```

### 4.3 Формат backlog-записи

Если в репозитории уже есть общий backlog/plan/TZ-файл, использовать его стиль. Если подходящего файла нет, создать:

```text
docs/backlog/ui-performance-upgrade.md
```

Формат задачи:

```markdown
### UPERF-001: Название задачи

Status: todo | doing | blocked | done
Priority: P0 | P1 | P2
Area: ui | render | streaming | meshing | network | tests | docs

#### Problem
Что болит.

#### Hypothesis
Почему это может помочь.

#### Files
- `path/to/file.py`

#### Plan
- [ ] Шаг 1
- [ ] Шаг 2
- [ ] Шаг 3

#### Tests
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run pyright`
- [ ] `uv run pytest -m unit`
- [ ] `uv run pytest -m integration`
- [ ] `uv run pytest -m smoke`

#### Metrics
Before:
- FPS:
- avg frame ms:
- p95 frame ms:
- draw calls:
- visible sections:
- triangles:
- notes:

After:
- FPS:
- avg frame ms:
- p95 frame ms:
- draw calls:
- visible sections:
- triangles:
- notes:

#### Acceptance
- [ ] Поведение не сломано.
- [ ] Тесты зелёные.
- [ ] Метрика улучшилась или причина отсутствия улучшения записана.
```

## 5. Phase 0 — Baseline profiling before changes

Цель: перестать гадать.

### 5.1 Добавить frame timing breakdown

Добавить lightweight profiling в debug overlay и/или отдельный benchmark:

```text
frame_total_ms
fixed_update_ms
world_update_ms
world_render_ms
ui_render_ms
streaming_update_ms
mesh_poll_upload_ms
entity_update_ms
network_poll_ms
draw_calls
visible_sections
triangles
mesh_queue
pending_chunks
```

Важно: не собирать эти метрики дорогим способом каждый кадр в release. Debug/profiling режим должен иметь throttling.

### 5.2 Добавить режимы диагностики

Временно или через config/dev flags:

```toml
[development]
profile_frame = true
disable_hud = false
disable_ui = false
disable_streaming_update = false
disable_entities = false
disable_local_network = false
```

Если не хочется добавлять все flags сразу, начать с двух:

```text
disable_hud
profile_frame
```

### 5.3 Acceptance

```text
- Можно увидеть, где тратится кадр: world render, UI, update, network, streaming.
- benchmark-frame-streaming не заменяет реальный GameWindow benchmark, потому что он не меряет полный HUD/UI/input/network path.
- Есть файл/лог с before numbers.
```

## 6. Phase 1 — UI/HUD performance triage

### 6.1 Тест: отключить HUD

В `GameWindow.on_draw()` после world render временно/через flag не рисовать:

```text
debug_label
hud_top_left_label
crosshair
hotbar
health
held hand/item
status label
inventory
text input
```

Если FPS заметно вырос, UI/HUD является bottleneck.

### 6.2 Исправить частое обновление текста

Сейчас HUD/debug text может обновляться каждый кадр. Нужно:

```text
- обновлять FPS/debug strings 5 раз в секунду;
- не менять Label.text, если текст не изменился;
- отдельный detailed debug overlay обновлять реже;
- минимальный HUD в обычном режиме.
```

### 6.3 Батчинг UI

Перевести постоянный HUD на `pyglet.graphics.Batch`:

```text
- hotbar rectangles;
- hotbar item sprites;
- key labels;
- hearts;
- crosshair;
- held item/hand;
- main HUD label.
```

### 6.4 Acceptance

```text
- HUD визуально совпадает или выглядит лучше.
- Нет потери mouse/keyboard behavior.
- UI/HUD render time в profiler меньше.
- Smoke test создаёт окно, рендерит меню и игровой кадр.
```

## 7. Phase 2 — Новый игровой UI toolkit

Цель: заменить ручное меню на маленький собственный game UI framework.

### 7.1 Создать модуль UI

Рекомендуемая структура:

```text
src/voxel_sandbox/render/ui/
    theme.py
    geometry.py
    widgets.py
    layout.py
    screens.py
    renderer.py
```

Можно адаптировать под текущую структуру, если уже есть `render/ui`.

### 7.2 Theme

Создать `UiTheme`:

```python
@dataclass(frozen=True, slots=True)
class UiTheme:
    font_name: str
    title_size: int
    body_size: int
    button_width: int
    button_height: int
    spacing: int
    panel_padding: int
    background_color: tuple[int, int, int, int]
    panel_color: tuple[int, int, int, int]
    panel_border_color: tuple[int, int, int, int]
    button_color: tuple[int, int, int, int]
    button_hover_color: tuple[int, int, int, int]
    button_pressed_color: tuple[int, int, int, int]
    text_color: tuple[int, int, int, int]
    muted_text_color: tuple[int, int, int, int]
    accent_color: tuple[int, int, int, int]
```

Стиль Veilstone:

```text
- тёмный камень/сланец;
- тёплый золотой accent;
- холодный сине-серый фон;
- мягкие borders;
- hover glow;
- pressed offset на 1–2 px;
- disabled opacity.
```

### 7.3 Widgets

Минимальные виджеты:

```text
UIRoot
ScreenView
Panel
Button
TextButton
IconButton
Label
TextInput
ListBox
WorldCard
SettingsRow
ToggleRow
SliderRow, optional later
```

Каждый widget должен иметь:

```python
bounds
visible
enabled
hovered
pressed
focusable
contains(x, y)
layout(...)
draw(...)
on_mouse_motion(...)
on_mouse_press(...)
on_mouse_release(...)
on_key_press(...)
```

### 7.4 Layout

Сделать простые layout helpers:

```text
centered_column
vertical_stack
horizontal_row
panel_with_title
scroll_list
```

Цель: не задавать вручную `label.x = ...` для каждого пункта меню.

### 7.5 Screens

Переписать/обернуть текущие screens:

```text
MainMenuScreen
SingleplayerScreen
WorldSelectScreen
CreateWorldScreen
MultiplayerScreen
SettingsScreen
ControlsScreen
AudioScreen
PauseMenuScreen
```

### 7.6 Визуальные требования к меню

Главное меню:

```text
- крупный title "Veilstone";
- subtitle/version;
- фон: sky renderer, затемнённый world snapshot или procedural background;
- центральная колонка кнопок;
- footer с подсказками;
- hover sound optional;
- ESC/back behavior.
```

Выбор мира:

```text
- список карточек миров;
- название мира;
- seed;
- дата последнего изменения, если доступна;
- кнопки Load, Create, Back;
- empty state “No saved worlds found”.
```

Settings:

```text
- rows вместо простого списка текста;
- toggle для clouds/vsync/postprocess;
- cycle row для shadows/difficulty;
- отдельные секции Graphics / Audio / Controls.
```

### 7.7 Acceptance

```text
- Стартовое меню выглядит как игровой интерфейс, не как debug list.
- Мышь и клавиатура работают.
- Existing menu commands продолжают работать.
- Main menu smoke test проходит.
- Нет PySide/PyQt/pygame dependency.
```

## 8. Phase 3 — Fast frustum culling

Цель: убрать NumPy/Python allocations на каждую секцию каждый кадр.

### 8.1 Проблема

Текущий AABB frustum test не должен создавать массивы/списки для каждой секции в каждом кадре. На больших render_distance это убивает CPU.

### 8.2 План

Сделать:

```text
- extract_frustum_planes(matrix) один раз за кадр;
- aabb_visible_fast(planes, bounds) без NumPy allocation;
- кэшировать bounds в GpuSectionMesh или рядом с key;
- заменить старый aabb_intersects_frustum в hot path;
- оставить unit tests на equivalence со старой функцией.
```

### 8.3 Tests

```text
- unit test: random AABB внутри/снаружи frustum даёт такой же результат, как старая функция;
- unit test: bounds для SectionCoord корректные;
- smoke test: мир рендерится;
- benchmark-frame-streaming before/after.
```

### 8.4 Acceptance

```text
- В render loop нет per-section NumPy array allocation для culling.
- FPS/frame time лучше или documented no-regression.
- Визуально секции не пропадают ошибочно.
```

## 9. Phase 4 — Separate render from streaming/update

### 9.1 Проблема

Render path должен рисовать, а не запускать тяжёлую работу по streaming/generation scheduling.

### 9.2 План

Разделить:

```text
fixed_update / world_update:
    - player/entities/audio/network;
    - streamer.update(...);
    - schedule mesh tasks;
    - poll completed mesh tasks with budget.

on_draw / render:
    - только draw current state;
    - без запуска новых worldgen jobs;
    - без relight/remesh scheduling, кроме safe queued uploads.
```

Если полный перенос сложный, сделать промежуточно:

```text
- streamer.update throttled до 5–10 раз/сек;
- max new pending chunks per update;
- max completed chunks per update;
- max mesh uploads per frame оставить budgeted.
```

### 9.3 Acceptance

```text
- on_draw не делает тяжелый streamer scheduling каждый кадр.
- При стоянии на месте frame time стабильнее.
- При движении чанки продолжают грузиться.
- Нет race/regression в multiplayer/remote mode.
```

## 10. Phase 5 — Fast singleplayer mode

### 10.1 Проблема

Singleplayer сейчас может быть архитектурно server-authoritative, но на слабом CPU постоянный localhost server/client overhead мешает FPS.

### 10.2 План

Добавить режим:

```text
singleplayer_fast:
    - default для обычной одиночки;
    - не стартует LanServer и ClientSession сразу;
    - server стартует только по Open to LAN;
    - block actions применяются напрямую к local world;
    - structure commands работают через local authority abstraction.
```

Сохранить:

```text
multiplayer:
    - dedicated server;
    - client connect;
    - Open to LAN;
    - current protocol tests.
```

Лучше не удалять текущий путь, а сделать abstraction:

```text
WorldAuthority
    LocalWorldAuthority
    NetworkWorldAuthority
```

### 10.3 Tests

```text
- unit: LocalWorldAuthority applies block actions.
- integration: Singleplayer create/load world without network session.
- integration: Open to LAN starts LanServer and accepts client.
- smoke: start game, create world, render frame.
```

### 10.4 Acceptance

```text
- Одиночка работает без socket до Open to LAN.
- Multiplayer не сломан.
- FPS/update time лучше или documented no-regression.
```

## 11. Phase 6 — Remesh/relight granularity

### 11.1 Проблема

Изменение одного блока не должно пересобирать слишком много секций/чанков.

### 11.2 Правила remesh

При изменении блока:

```text
- remesh секцию, где блок изменён;
- если блок на границе секции, remesh соседнюю секцию;
- если блок меняет прозрачность/opacity, проверить lighting impact;
- если блок является light emitter или удалён light emitter, запускать light update;
- если обычный solid -> air или air -> solid без света, не relight 3x3 chunk neighborhood без нужды;
- water mesh отдельно от opaque mesh, если возможно.
```

### 11.3 Dirty section queue

Добавить очередь:

```text
dirty_opaque_sections: set[SectionCoord]
dirty_water_sections: set[SectionCoord]
dirty_light_chunks: set[ChunkCoord]
```

Process:

```text
- collect dirty;
- coalesce duplicates;
- process limited budget per update;
- avoid resubmitting same section repeatedly if pending revision exists.
```

### 11.4 Tests

```text
- unit: block inside section marks one section dirty.
- unit: block on x/y/z border marks neighbor section.
- unit: non-light block edit does not relight unrelated 3x3 chunks.
- integration: break/place block updates rendered mesh.
- integration: water update affects water mesh.
- benchmark-mesher before/after.
```

### 11.5 Acceptance

```text
- Ломание/постановка блока не вызывает крупный spike.
- Визуальные соседние грани обновляются корректно.
- Освещение не ломается для lantern/skylight cases.
```

## 12. Phase 7 — Mesh task batching

### 12.1 Проблема

Section-level process tasks могут быть слишком мелкими. IPC и serialization могут съесть выигрыш.

### 12.2 План

Сравнить два подхода:

```text
A. current: one future per section
B. improved: one future per chunk/column returning multiple section meshes
```

Не менять сразу, сначала добавить benchmark:

```text
benchmark-mesher:
    - sections/sec;
    - chunk columns/sec;
    - process backend vs thread backend;
    - IPC overhead estimate;
    - mesh bytes generated.
```

Если batching быстрее:

```text
- SectionMeshWorker.submit_chunk(...)
- build neighborhoods for all sections of chunk in one worker task;
- return dict[SectionCoord, CompletedMesh]
```

### 12.3 Acceptance

```text
- Меньше futures.
- Меньше snapshot/IPC overhead.
- Нет visual regression.
```

## 13. Phase 8 — Mesh data compactness, later optimization

Не делать первым шагом. Но для будущего render_distance 8–12 важно уменьшить размер вершин.

Сейчас типичный voxel vertex может хранить много float-атрибутов. Дальше можно упаковать:

```text
position: uint8 x/y/z inside section
uv: uint16 or generated in shader
normal: int8/uint8 encoded direction
sky/block light: uint8
ao: uint8
atlas index: uint16 instead of full atlas rect per vertex
```

Но это сложнее и требует аккуратных shader changes.

Acceptance для будущего:

```text
- vertex bytes меньше;
- visual parity;
- benchmark показывает меньше upload bandwidth / memory.
```

## 14. Visual polish backlog

### UI-001: Theme and Button component

Priority: P0

```text
Create reusable Button with normal/hover/pressed/disabled states.
Use it in MainMenuScreen first.
```

Acceptance:

```text
- Buttons are visually styled.
- Mouse hover changes appearance.
- Pressed state visible.
- Keyboard selection still works.
- Smoke test passes.
```

### UI-002: Main menu redesign

Priority: P0

```text
Replace simple text list with styled panel and centered button column.
```

Acceptance:

```text
- Looks like game menu.
- Supports Singleplayer, Multiplayer, Settings, Exit.
- ESC/back works.
```

### UI-003: World select cards

Priority: P1

```text
Replace plain world selection text input/list with WorldCard list.
```

Acceptance:

```text
- Empty state shown.
- Worlds show name/seed/modified date if available.
- Create, Load, Back are clear.
```

### UI-004: Settings rows

Priority: P1

```text
Graphics/Audio/Controls settings become sections with rows.
```

Acceptance:

```text
- VSync/clouds/postprocess are toggles.
- Shadow quality/difficulty are cycle rows.
- Saved settings still persist.
```

### UI-005: UI batching

Priority: P0/P1

```text
Use pyglet batch/group for menu/HUD drawing.
```

Acceptance:

```text
- Fewer draw calls / lower ui_render_ms.
- No visual regression.
```

## 15. Performance backlog

### PERF-001: Add real frame profiler

Priority: P0

```text
Measure GameWindow frame breakdown, not only world_renderer benchmark.
```

Acceptance:

```text
- Debug overlay or log shows frame_total/world_render/ui_render/fixed_update/network/streaming.
```

### PERF-002: Fast frustum culling

Priority: P0

```text
Replace per-section NumPy allocation culling with plane-based scalar culling.
```

Acceptance:

```text
- Unit equivalence tests.
- Better frame time or documented result.
```

### PERF-003: HUD update throttling

Priority: P0

```text
Update HUD text at 5 Hz and batch static HUD.
```

Acceptance:

```text
- ui_render_ms lower.
- FPS/debug text still correct enough.
```

### PERF-004: Move streamer work out of render path

Priority: P1

```text
Render should draw current state; update should stream/schedule.
```

Acceptance:

```text
- Lower frame spikes.
- Chunk loading still works.
```

### PERF-005: Fast singleplayer without localhost network

Priority: P1

```text
Do not start LAN server/client until Open to LAN.
```

Acceptance:

```text
- Singleplayer works offline/direct.
- Open to LAN still works.
- Multiplayer tests pass.
```

### PERF-006: Dirty section remesh

Priority: P1

```text
Remesh only affected sections and neighbors.
```

Acceptance:

```text
- Block edit no longer schedules whole chunk neighborhoods unless needed.
```

### PERF-007: Chunk-level mesh batching

Priority: P2

```text
Investigate batching section meshing tasks per chunk/column.
```

Acceptance:

```text
- Benchmark proves improvement before replacing default.
```

### PERF-008: Low-end preset

Priority: P0

```text
Add potato/low preset for i3/RX550-class hardware.
```

Suggested settings:

```toml
[window]
vsync = false

[world]
render_distance = 2
generation_workers = 1
meshing_workers = 1
chunk_uploads_per_frame = 1
mesh_uploads_per_frame = 1

[graphics]
smooth_lighting = false
ambient_occlusion = false
fog = true
shadow_quality = "off"
clouds = false
postprocess = false
```

Acceptance:

```text
- Preset can be selected or documented.
- Target: stable 60 FPS at render_distance=2 on low-end hardware if possible.
```

## 16. Integration and smoke test requirements

### 16.1 UI tests

Add tests where practical:

```text
- Button hover/click state.
- Button action dispatch.
- Keyboard navigation.
- Screen transition MainMenu -> Singleplayer -> Back.
- Settings row toggles update settings object.
```

These can be unit tests without OpenGL if UI model is separated from renderer.

### 16.2 Render smoke tests

Existing smoke tests should continue to cover:

```text
- OpenGL context creation.
- Shader compilation.
- Main menu render once.
- World render once.
- Dedicated server entry point.
```

Add or update smoke tests for:

```text
- New MainMenuScreen render.
- New WorldSelectScreen render.
- New SettingsScreen render.
```

### 16.3 Performance tests

Performance tests should not be overly strict in CI unless stable. Prefer:

```text
- print metrics;
- compare relative in local development;
- keep sanity bounds only if reliable.
```

Example:

```text
benchmark-frame-streaming:
    avg <= previous documented target on dev machine
    p95 recorded
    draw calls/visible sections recorded
```

### 16.4 Regression tests

For optimization work:

```text
- culling equivalence test;
- dirty section marking test;
- singleplayer/local authority behavior test;
- remesh border neighbor test;
- lighting affected cases test;
- multiplayer/open-to-LAN integration test.
```

## 17. Suggested Codex task order

Give Codex tasks in this order:

```text
1. Create docs/backlog/ui-performance-upgrade.md using this plan.
2. Add GameWindow frame profiler and profile overlay/log.
3. Add disable_hud diagnostic flag and measure UI cost.
4. Implement fast frustum culling with tests.
5. Throttle HUD text updates.
6. Create UI theme + Button component.
7. Replace MainMenu with styled button layout.
8. Add WorldCard-based world select.
9. Move streamer scheduling out of render path or throttle it.
10. Add fast singleplayer/local authority mode.
11. Add dirty section remesh queue.
12. Benchmark chunk-level mesh task batching.
```

Do not let Codex jump to phase 8 before phases 0–4.

## 18. Suggested first prompt for Codex

```text
Read docs/UPDATE_UI_PERFORMANCE_PLAN.md and README.md.

Start with Phase 0 only:
- create/update docs/backlog/ui-performance-upgrade.md;
- add lightweight GameWindow frame profiling;
- expose frame_total_ms, world_render_ms, ui_render_ms, fixed_update_ms, network_poll_ms, streaming/mesh upload timing if easy;
- throttle profiler text/log output to avoid adding large overhead;
- add/update tests where practical;
- run ruff, pyright, pytest, and benchmark-frame-streaming;
- do not redesign UI yet;
- report before metrics and changed files.
```

## 19. Definition of Done for the whole update

The upgrade is complete when:

```text
- Main menu and world selection look like intentional game UI.
- UI uses reusable widgets/theme/layout instead of scattered manual labels.
- HUD cost is measured and reduced.
- Frame profiler exists.
- Frustum culling no longer allocates per section each frame.
- Render path is less mixed with world streaming work.
- Singleplayer can run without unnecessary localhost networking until Open to LAN.
- Block edits/remesh are more granular.
- Integration/smoke/unit tests pass.
- Backlog records decisions, before/after metrics, and remaining work.
```

## 20. Final note

The goal is not to beat Minecraft immediately. The goal is to make Veilstone’s architecture more game-engine-like:

```text
measure -> isolate bottleneck -> small optimization -> tests -> metrics -> next step
```

Do not optimize blindly. Every performance change should leave either an improvement or a useful measurement.
