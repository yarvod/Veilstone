# ТЗ для Codex: Python Voxel Sandbox Engine

> Цель: разработать полноценную voxel sandbox игру на Python в духе классического Minecraft-era sandbox survival, но без копирования ассетов, названий, текстур, звуков, UI и защищённого контента Minecraft.  
> Игра должна иметь процедурный блочный мир, чанки, генерацию, воду, мобы, предметы, крафт, инвентарь, локальный мультиплеер, настройки, шейдеры, тени, красивое освещение, модульную архитектуру, тесты и понятный entry point.

---

## 0. Главная установка для Codex

Не пытайся сделать всё одним огромным файлом.

Проект должен разрабатываться как production-like Python game engine:

- чистая, понятная архитектура;
- разделение домена, движка, инфраструктуры, рендера и приложения;
- стабильный entry point;
- тестируемая логика без OpenGL;
- hot-reload конфигов/ресурсов там, где это просто;
- профилирование с самого начала;
- строгая оптимизация чанков, мешей и сетевого протокола;
- минимизация Python-объектов в горячих циклах;
- максимальный перенос тяжёлой работы в GPU, NumPy, compiled extensions или батчевые структуры.

---

## 1. Реалистичная формулировка цели

Нужно сделать не буквальный Minecraft, а **оригинальную voxel sandbox game**.

Разрешено реализовать похожие общие игровые механики:

- блочный мир;
- чанки;
- добыча и установка блоков;
- survival;
- крафт;
- инвентарь;
- мобы;
- вода;
- освещение;
- структуры;
- локальная сетевая игра;
- day/night cycle;
- настройки графики и управления.

Нельзя копировать:

- оригинальные текстуры Minecraft;
- звуки Minecraft;
- названия мобов и предметов, если они являются узнаваемыми элементами бренда;
- UI один-в-один;
- конкретные художественные ассеты;
- код Minecraft;
- сетевой протокол Minecraft.

Нужно использовать свои ассеты, свои названия, свои структуры и свой визуальный стиль.

---

## 2. Целевые платформы

Минимально поддержать:

- Windows 10/11;
- macOS Apple Silicon и Intel;
- Linux, если не ломает архитектуру.

Целевой компьютер:

- средний ноутбук;
- MacBook Air/Pro последних нескольких лет;
- дискретная видеокарта не обязательна, но желательна для высоких настроек.

Целевая производительность:

- 60 FPS на средних настройках;
- 30 FPS на слабой машине;
- render distance 8 чанков минимум;
- render distance 12–16 чанков на средних/хороших машинах;
- локальная сеть 2–8 игроков;
- серверный tickrate 20 TPS;
- клиентский render FPS независим от server tickrate.

---

## 3. Рекомендуемый стек

### 3.1 Runtime

- Python 3.12+.
- `uv` как обязательный package/project manager. Poetry не использовать.
- Ruff для lint/format.
- Pyright или mypy для type checking.
- pytest для тестов.

### 3.2 Графика

Основной вариант:

- `pyglet` — окно, ввод, OpenGL context, event loop, звук.
- `moderngl` — OpenGL 3.3+ rendering backend.
- `numpy` — компактные массивы чанков, вершин, индексов.
- `Pillow` — загрузка/сборка texture atlas.
- GLSL shaders — lighting, fog, water, shadows, postprocessing.

Почему так:

- pyglet даёт кроссплатформенное окно, ввод и OpenGL-контекст;
- ModernGL — высокопроизводительный Python wrapper для OpenGL;
- тяжёлый рендер уходит в GPU;
- Python остаётся управляющим слоем.

### 3.3 Сеть

- `asyncio` TCP или UDP-like поверх `asyncio.DatagramProtocol`.
- Для MVP использовать TCP.
- Для action game можно перейти на UDP.
- `msgpack` для бинарной сериализации.
- `zstandard` опционально для сжатия чанков.
- Авторитарный сервер.

### 3.4 Данные

- `pydantic` или `msgspec` для конфигов и сериализации.
- TOML/YAML/JSON для настроек.
- SQLite или файловое region-хранилище для мира.
- Бинарный формат чанков.

### 3.5 Опционально для производительности

- `numba` для meshing/lighting, если совместимость нормальная.
- `cython` или `mypyc` для самых горячих участков.
- `multiprocessing` для генерации чанков.
- worker threads/processes для meshing.
- `py-spy`, `scalene`, `cProfile`, `tracy` bindings опционально.


### 3.6 Package management через uv

Проект должен использовать только `uv`.

Обязательные команды разработки:

```bash
uv sync
uv run python -m voxel_sandbox
uv run python -m voxel_sandbox client --connect 127.0.0.1:25565
uv run python -m voxel_sandbox server
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-worldgen
uv run python -m voxel_sandbox benchmark-physics
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-streaming
uv run python -m voxel_sandbox benchmark-frame-streaming
uv run python -m voxel_sandbox benchmark-network
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright
```

`pyproject.toml` должен содержать:

- project metadata;
- runtime dependencies;
- dev dependencies;
- scripts/entry-points;
- Ruff config;
- pytest config;
- pyright/mypy config.

Запрещено:

- добавлять Poetry lock/config;
- добавлять Pipenv;
- писать инструкции через global pip install;
- требовать ручной установки зависимостей вне `uv sync`.

Разрешено:

- использовать optional dependency groups:

```toml
[dependency-groups]
dev = [...]
perf = [...]
tools = [...]
```


---

## 4. Архитектурное решение

Не использовать “чистую архитектуру дяди Боба” буквально и фанатично для всего проекта.

Для game engine это может создать слишком много абстракций в горячем коде. Нужен гибрид:

- Clean Architecture для доменной логики, настроек, сохранений, сети, game rules.
- Data-Oriented Design для чанков, мешей, блоков, света, физики и рендера.
- ECS-lite для entity/mob/item систем.
- Dependency Injection на уровне application composition root, но не в горячих циклах.

### 4.1 DI

Использовать DI можно, но аккуратно.

Подходит:

- создание сервисов в `bootstrap.py`;
- передача зависимостей в application layer;
- конфиги;
- логгер;
- asset manager;
- network client/server;
- repositories;
- game services.

Не подходит:

- создание блока через контейнер;
- каждый mob tick через DI;
- каждый render call через интерфейсы;
- каждый face/vertex/chunk через объекты.

Можно использовать `dishka`, но не обязательно. Если используем, то только на верхнем уровне.

Правило:

> DI container не должен появляться внутри hot path: chunk meshing, render loop, entity simulation, physics, networking packet loop.

### 4.2 Слои

```text
src/voxel_sandbox/
  app/
    bootstrap.py
    main_client.py
    main_server.py
    game_app.py
    settings.py

  domain/
    blocks/
    items/
    crafting/
    inventory/
    entities/
    combat/
    world_rules/
    events/

  engine/
    world/
    chunks/
    generation/
    lighting/
    physics/
    ecs/
    time/
    math/

  render/
    backend/
    shaders/
    meshes/
    materials/
    texture_atlas/
    camera/
    ui/
    postprocess/

  net/
    protocol/
    client/
    server/
    replication/
    snapshots/
    lan_discovery/

  infrastructure/
    assets/
    storage/
    logging/
    config/
    profiling/

  tools/
    asset_packer.py
    world_viewer.py
    benchmark_mesher.py
    benchmark_network.py

tests/
  unit/
  integration/
  perf/
```

---


## 4.3 Расширяемая gameplay-архитектура

Игра должна проектироваться не как набор захардкоженных механик, а как расширяемая платформа для странных существ, магии, структур, событий и интерактивного мира.

Нужно заложить следующие расширяемые системы:

- entity/component system для мобов, игроков, предметов, снарядов и интерактивных объектов;
- animation graph для частей тела, костей, процедурных движений и реакций;
- articulated model system для существ с несколькими подвижными частями;
- block entity system для сложных блоков и построек;
- structure entity system для больших подвижных или интерактивных конструкций;
- event/bus system для игровых событий;
- scripting/data-driven definitions для мобов, предметов, структур, биомов, достижений и квестов;
- behavior tree или utility AI для мобов;
- timeline/sequence system для катсцен, ритуалов, боссов и структурных событий;
- trigger system для зон, порталов, данжей, прогресса истории и достижений.

Пример: моб не должен быть просто `Mob(type="wolf")`. Он должен собираться из данных:

```text
MobDef
  model: blocky_model_or_gltf
  skeleton: bones/parts
  animations: idle/walk/run/attack/hurt/custom
  movement_controller: ground / flying / crawling / climbing / swimming / teleporting
  behavior_tree: data-driven
  loot_table
  sounds
  particles
  network_replication_profile
```

Пример: структура не должна быть только набором блоков. Некоторые структуры должны иметь активное состояние:

```text
StructureEntity
  placed blocks
  anchor position
  active parts
  animation state
  triggers
  corruption/magic level
  loot state
  boss state
  network replicated state
```

## 4.4 Animation and articulated parts architecture

Нужно поддержать необычные движения мобов и их частей тела:

- idle procedural motion;
- walk cycles;
- attack wind-up/release/recover;
- head tracking;
- limb IK-lite;
- tail/tentacle wave motion;
- wing flapping;
- crawling/spider-like gait;
- swimming motion;
- flying bob/swoop motion;
- segmented worm/snake movement;
- boss phase animations;
- hit reactions;
- death animations.

Минимальная архитектура:

```text
render/model/
  ModelDef
  ModelPart
  SkeletonDef
  BoneDef
  AnimationClip
  AnimationGraph
  Pose
  PoseBlender
  ProceduralAnimator
```

Компоненты:

```text
SkeletonComponent
AnimationStateComponent
ProceduralMotionComponent
LookAtTargetComponent
AttachmentPointsComponent
```

Системы:

```text
AnimationSystem
ProceduralMotionSystem
PoseUploadSystem
EntityRenderSystem
```

Требование:

- логика анимации должна быть отделена от конкретного моба;
- новые движения должны добавляться через новые animation controllers/data definitions;
- анимации должны быть реплицируемы по сети компактно: состояние, фаза, seed, animation id, а не полный pose каждый tick;
- на клиенте анимации интерполируются локально.

## 4.5 Movable structures and interactive machines

Архитектура должна позволять делать подвижные штуки не только у мобов, но и у построек:

Примеры:

- вращающиеся магические алтари;
- открывающиеся каменные ворота;
- мосты, которые собираются из блоков;
- лифты;
- портальные арки;
- данжевые двери с фазами;
- босс-арены, меняющие геометрию;
- мельницы, цепи, шестерни, платформы;
- живые деревья/корни, которые двигаются;
- кристаллы, которые пульсируют и освещают местность.

Для этого нужны:

- `BlockEntity` для одного сложного блока;
- `MultiBlockStructure` для группы блоков;
- `StructureEntity` для активной структуры;
- локальная система координат структуры;
- отдельная collision proxy;
- отдельный render proxy;
- state machine;
- network replication;
- save/load state.

Нельзя каждый кадр физически переставлять тысячи блоков ради анимации. Для подвижных структур использовать:

- render-time transforms;
- instanced parts;
- collision update только при смене фазы;
- baked meshes for states;
- event-driven updates.


## 5. Entry points

Основной player-facing entry point должен быть один:

```bash
uv run python -m voxel_sandbox
```

Он открывает игровой Main Menu:

```text
Main Menu
  ├── Singleplayer
  │    └── Create/Load World
  │         └── Pause Menu
  │              └── Open to LAN
  ├── Multiplayer
  │    ├── Join LAN World
  │    └── Direct Connect
  ├── Settings
  └── Exit
```

Этот запуск открывает полное игровое приложение: main menu, settings,
singleplayer и multiplayer UI. Обычный игрок не должен выбирать между `client`, `server`
и `host`.

Технические entry points существуют только для development, testing, dedicated LAN hosting
и debugging:

```bash
uv run python -m voxel_sandbox server
uv run python -m voxel_sandbox client --connect 127.0.0.1:25565
uv run python -m voxel_sandbox benchmark-mesher
uv run python -m voxel_sandbox benchmark-worldgen
uv run python -m voxel_sandbox benchmark-physics
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-network
```

`server` и `client --connect` не являются primary user experience. Отдельного player-facing
`host` mode нет: обычный hosting выполняется через `Singleplayer -> Pause Menu -> Open to LAN`.

Обязательная модель запуска и authority:

```text
Singleplayer:
  Client -> local in-process authoritative server

Open to LAN:
  Client -> existing local in-process authoritative server becomes LAN-visible
  Other clients -> connect to that server over LAN

Dedicated server:
  Standalone authoritative server process, advanced/developer mode only
```

Singleplayer и multiplayer обязаны использовать одну game simulation и одни server-side rules.
Нельзя реализовывать singleplayer как отдельную неавторитарную ветку gameplay-логики.

---

## 6. Ключевые performance-принципы

### 6.1 Не делать

Нельзя:

- создавать отдельный Python-объект для каждого блока;
- рендерить каждый блок отдельным draw call;
- хранить мир как dict из миллионов объектов;
- пересобирать все чанки каждый кадр;
- делать lighting BFS по всему миру каждый кадр;
- отправлять весь мир по сети каждый tick;
- делать физику для всех мобов на всей карте.

### 6.2 Делать

Нужно:

- хранить блоки чанка в `numpy.ndarray` или компактном packed buffer;
- один mesh на chunk section;
- один или несколько VBO/IBO на chunk section;
- dirty flags для чанков;
- meshing только при изменениях;
- async очередь генерации и remeshing;
- frustum culling;
- occlusion culling на уровне чанков, если успеем;
- greedy meshing;
- texture atlas;
- batch rendering;
- LOD/fog/render distance;
- сетевые snapshots + deltas;
- interest management вокруг игрока.

---

## 7. Размеры мира и чанков

Рекомендуемая структура:

```text
Chunk = 16 x 256 x 16
ChunkSection = 16 x 16 x 16
Region = 32 x 32 chunks
```

Для простоты MVP можно начать:

```text
Chunk = 16 x 128 x 16
Section = 16 x 16 x 16
```

Хранение:

```python
blocks: np.ndarray[uint16]  # block_id per voxel
block_light: np.ndarray[uint8]
sky_light: np.ndarray[uint8]
metadata: np.ndarray[uint8]  # orientation/growth/water-level/etc
```

Block ID:

- `0` reserved for air;
- `1..N` regular blocks;
- flags/material properties separate from ID.

---

## 8. Рендеринг

### 8.1 Pipeline

Минимальный pipeline:

```text
1. update camera
2. collect visible chunk sections
3. frustum culling
4. bind world shader
5. bind texture atlas
6. draw opaque chunk meshes front-to-back
7. draw alpha-tested foliage
8. draw transparent water back-to-front or approximate
9. draw entities/items
10. draw particles
11. draw skybox/sun/moon/clouds
12. postprocess
13. UI
```

### 8.2 Shaders

Нужны GLSL shaders:

- `chunk_opaque.vert`
- `chunk_opaque.frag`
- `chunk_alpha.vert`
- `chunk_alpha.frag`
- `water.vert`
- `water.frag`
- `entity.vert`
- `entity.frag`
- `shadow_depth.vert`
- `shadow_depth.frag`
- `sky.vert`
- `sky.frag`
- `ui.vert`
- `ui.frag`

### 8.3 Освещение

MVP:

- directional sun light;
- ambient term;
- fog;
- baked vertex light из block/sky light.

Дальше:

- sky light propagation;
- block light propagation;
- smooth lighting;
- ambient occlusion по вершинам;
- shadow mapping от солнца;
- cascaded shadow maps опционально;
- water caustics/fake reflections опционально.

Требования к voxel lighting implementation:

- block light распространяется инкрементальным flood fill/BFS по voxel grid, а не CPU raycast
  от источника к каждому fragment/block;
- skylight хранится в voxel light data и должен корректно продолжаться через границы
  chunk/section;
- smooth lighting и AO на вершинах обязаны брать halo соседних section/chunk, а не считать
  отсутствующие локальные данные нулевым светом;
- triangulation quad должна выбирать диагональ по vertex light/AO или иным способом исключать
  заметные диагональные и крестообразные градиенты;
- изменение блока/источника света должно инвалидировать только затронутые lighting regions и
  meshes; полный пересчёт всего мира каждый кадр запрещён.

### 8.4 Тени

Реализовать в этапах:

1. Fake contact shadow / ambient occlusion.
2. Simple shadow map для nearby chunks/entities.
3. Cascaded shadow maps, если FPS нормальный.

Солнечные тени реализуются на GPU через depth shadow map: один depth pass для видимых nearby
casters, затем lookup/PCF в world shader. Не трассировать отдельные CPU rays от солнца или
каждого источника света к блокам/fragment'ам. Локальные block lights в MVP не отбрасывают
динамические shadow maps: их затенение обеспечивается voxel propagation и AO.

Настройки:

- shadows off;
- low 512/1024;
- medium 2048;
- high 4096;
- shadow distance 32/64/96/128 blocks.

### 8.5 Вода

Вода должна быть отдельным material/render pass.

MVP:

- water block;
- прозрачность;
- анимированная UV;
- простая волна в vertex shader.

Дальше:

- water levels;
- flow direction;
- propagation simulation;
- underwater fog;
- reflection fake;
- refraction fake.

---

## 9. Meshing

### 9.1 MVP meshing

Сначала реализовать visible-face meshing:

- для каждого non-air блока;
- проверить 6 соседей;
- если сосед прозрачный или air — добавить грань;
- добавить UV по texture atlas;
- добавить light per vertex;
- добавить AO per vertex.

### 9.2 Greedy meshing

После MVP обязательно реализовать greedy meshing:

- объединять соседние coplanar faces одинакового материала;
- учитывать texture, light, AO, transparency;
- не объединять faces с разной освещённостью, если это портит визуал;
- отдельно opaque и transparent meshes.

### 9.3 Mesh format

Вершина должна быть packed:

```text
position: 3 x uint16 or float32
uv: 2 x uint16 normalized
normal/face_id: uint8
light: uint8 packed
ao: uint8
material/flags: uint16
```

Для MVP можно float32, но потом перейти на packed format.

---

## 10. World generation

### 10.1 Biomes

Биомы:

- plains;
- forest;
- desert;
- snowy;
- mountains;
- swamp;
- ocean;
- caves.

### 10.2 Terrain

Генерация:

- heightmap noise;
- temperature/humidity noise;
- biome blending;
- caves noise;
- ores distribution;
- trees;
- lakes;
- structures.

### 10.3 Structures

Структуры оригинальные, не копировать Minecraft.

Примеры:

- ruined watchtower;
- underground shrine;
- abandoned hut;
- stone circle;
- crystal cave;
- small village-like camp;
- mine entrance;
- floating ruins rare.

Структуры должны генерироваться deterministic от seed.

---

## 11. Blocks

Минимальный набор блоков:

- air;
- stone;
- dirt;
- grass;
- sand;
- gravel;
- clay;
- snow;
- log;
- leaves;
- planks;
- glass;
- water;
- lava-like hazard liquid;
- coal ore;
- iron ore;
- copper-like ore;
- gold-like ore;
- rare crystal ore;
- workbench;
- furnace-like processor;
- chest;
- door;
- torch;
- ladder;
- farmland;
- crop;
- flower;
- tall grass.

Block properties:

```python
@dataclass(frozen=True, slots=True)
class BlockDef:
    id: int
    key: str
    name: str
    material: Material
    hardness: float
    blast_resistance: float
    is_solid: bool
    is_opaque: bool
    is_transparent: bool
    is_fluid: bool
    emits_light: int
    texture_top: str
    texture_side: str
    texture_bottom: str
    drops: list[DropDef]
    tool_required: ToolType | None
```

---

## 12. Items, inventory, crafting

### 12.1 Items

Item types:

- block item;
- tool item;
- weapon item;
- food item;
- resource item;
- armor item;
- bucket-like fluid container.

### 12.2 Inventory

- hotbar 9 slots;
- backpack grid;
- stack size;
- drag/drop;
- split stack;
- quick move;
- item pickup;
- item drop.

### 12.3 Crafting

MVP:

- shapeless recipes;
- shaped recipes;
- 2x2 player crafting;
- 3x3 workbench crafting.

Дальше:

- furnace/processor recipes;
- fuel;
- smelting progress.

---

## 13. Entities

### 13.1 ECS-lite

Использовать ECS-lite:

```text
EntityId = int
Components stored in dense arrays/dicts
Systems update components
No heavy object hierarchy in hot path
```

Components:

- Transform;
- Velocity;
- Collider;
- Health;
- Inventory;
- MobAI;
- RenderModel;
- NetworkReplicated;
- Lifetime;
- ItemStack;
- PlayerInput.

### 13.2 Players

Player features:

- first-person controller;
- walking;
- jumping;
- sneaking optional;
- swimming;
- block interaction raycast;
- tool usage;
- health;
- hunger optional;
- damage;
- respawn.

### 13.3 Mobs

Минимум:

- passive walker;
- hostile melee mob;
- ranged mob optional;
- flying mob optional;
- water mob optional.

AI:

- idle;
- wander;
- flee;
- chase;
- attack;
- avoid water/lava;
- simple pathfinding near player;
- despawn when far.

Pathfinding не делать глобальным A* по миру для всех мобов. Использовать локальный coarse navigation + steering.

---

## 14. Physics and collision

### 14.1 Player physics

- AABB collision against voxel world;
- swept collision или axis-separated collision;
- gravity;
- jump;
- water drag;
- ladder movement;
- step-up optional.

### 14.2 Entities

- AABB;
- gravity;
- collision;
- basic knockback;
- item pickup radius.

### 14.3 Raycast

Voxel DDA raycast:

- block selection;
- block breaking;
- block placing;
- entity targeting optional.

---

## 15. Lighting simulation

MVP:

- skylight based on heightmap;
- torch light local BFS;
- light baked into chunk mesh.

Дальше:

- full sky light propagation;
- block light propagation across chunk borders;
- dirty light queues;
- relight affected region only.

Не пересчитывать освещение всего чанка при каждом изменении блока.

---

## 16. Save/load world

### 16.1 World folder

```text
saves/
  world_name/
    level.toml
    players/
    regions/
      r.0.0.vreg
      r.0.1.vreg
    indexes/
    stats/
```

### 16.2 Region format

Сделать простой бинарный контейнер:

- header;
- version;
- chunk index table;
- compressed chunk blobs;
- checksum optional.

Для MVP можно:

- one file per chunk;
- zstd/msgpack.

Потом перейти на region files.

---

## 17. Multiplayer LAN

### 17.1 Modes

- Singleplayer = game client + local in-process authoritative server.
- Open to LAN = existing singleplayer server becomes LAN-visible and enables LAN discovery.
- Join LAN World = client selects a discovered server from the Multiplayer menu.
- Direct Connect = client connects to an explicitly entered address.
- Dedicated LAN server = standalone advanced/developer server process.

Все режимы используют один server-authoritative simulation pipeline. `Open to LAN` не
создаёт второй мир и не перезапускает gameplay в другом режиме.

### 17.2 Authority

Сервер авторитарный:

- world state;
- player positions validated;
- block changes;
- mob AI;
- item drops;
- inventory operations;
- crafting;
- damage.

Клиент:

- input prediction;
- interpolation;
- local camera;
- rendering;
- UI;
- sends input commands;
- receives snapshots/deltas.

### 17.3 Protocol

Message types:

```text
C_HELLO
S_HELLO
C_JOIN
S_JOIN_ACCEPTED
C_PLAYER_INPUT
C_BLOCK_ACTION
C_INVENTORY_ACTION
C_CHAT
S_WORLD_CHUNK
S_CHUNK_DELTA
S_ENTITY_SNAPSHOT
S_PLAYER_STATE
S_CHAT
S_DISCONNECT
PING
PONG
```

Use binary frames:

```text
uint16 message_type
uint32 sequence
uint32 payload_length
bytes payload
```

Payload:

- MVP: msgpack.
- Optimized: custom binary.

### 17.4 Interest management

Сервер отправляет клиенту:

- чанки вокруг игрока;
- entities near player;
- deltas only for visible/relevant chunks;
- no far mobs.

### 17.5 LAN discovery

- UDP broadcast beacon.
- Host broadcasts server name, port, player count, world seed hash.
- Client shows LAN list.

---

## 18. UI and settings

### 18.1 Screens

- main menu;
- create world;
- load world;
- host LAN;
- join LAN;
- settings;
- pause;
- inventory;
- crafting;
- death/respawn;
- debug overlay.

### 18.2 Settings

Graphics:

- resolution;
- fullscreen;
- vsync;
- FOV;
- render distance;
- simulation distance;
- shadow quality;
- shadow distance;
- ambient occlusion;
- smooth lighting;
- water quality;
- particles;
- texture filtering;
- mipmaps;
- fog;
- max FPS.

Controls:

- key bindings;
- mouse sensitivity;
- invert Y;
- toggle sprint optional.

Audio:

- master;
- music;
- blocks;
- entities;
- UI.

Gameplay:

- difficulty;
- LAN max players;
- show debug overlay;
- autosave interval.

---

## 19. Asset pipeline

### 19.1 Textures

- свои текстуры 16x16, 32x32 или 64x64;
- texture atlas;
- mipmaps;
- optional normal/roughness atlas.

Tools:

```bash
python -m voxel_sandbox tools pack-atlas assets/textures
```

### 19.2 Models

Для mobs/items:

- simple blocky JSON model format;
- or glTF for non-block entities;
- cache GPU meshes.

### 19.3 Sounds

- свои звуки;
- OGG/WAV;
- positional audio optional.

---


## 20. Audio, music and ambience

Игра должна иметь полноценную аудио-архитектуру.

### 20.1 Audio systems

Нужно реализовать:

- music manager;
- ambience manager;
- positional SFX;
- UI sounds;
- block sounds;
- mob sounds;
- weather ambience;
- cave ambience;
- biome ambience;
- combat stingers;
- story/event music cues;
- volume groups.

Volume groups:

```text
master
music
ambient
blocks
mobs
player
ui
weather
network_players
```

### 20.2 Dynamic music

Музыка должна быть не просто random playlist. Нужна система состояний:

```text
calm_day
calm_night
cave
danger_near
combat
boss
magic_forest
ruins
deep_dark
victory
death
```

Переходы:

- fade in/out;
- crossfade;
- cooldown между треками;
- event stinger поверх ambient track.

### 20.3 Audio implementation

Для MVP можно использовать аудио возможности pyglet.

Архитектура должна быть такой, чтобы позже можно было заменить backend:

```text
AudioBackend Protocol
PygletAudioBackend
NullAudioBackend for tests/server
AudioEventBus
MusicDirector
AmbienceDirector
```

Сервер не должен проигрывать звук. Сервер отправляет игровые события, клиент решает, какой звук воспроизводить.

---

## 21. Story, progression and dark magic vibe

Игра должна иметь свободный sandbox, но поверх него — историю, которую можно проходить с друзьями.

Референс по ощущению: тёмный магический лес/измерение, прогресс через биомы, структуры, боссов, артефакты, достижения и открытия. Не копировать конкретные ассеты/названия из чужих модов.

### 21.1 Core fantasy

Рабочая концепция:

> Игроки попадают в мир, где обычная поверхность постепенно заражается древним сумрачным измерением. В глубине лесов, руин и пещер есть магические узлы. Игроки могут жить как в обычной песочнице, строить, исследовать, крафтить и играть по сети, но если идут по истории, они открывают новые биомы, ритуалы, структуры, боссов и способы менять мир.

Ключевые темы:

- сумрачное освещение;
- магические леса;
- руины;
- древние порталы;
- живые структуры;
- странные мобы;
- загадочные артефакты;
- кооперативные события;
- исследование без полного линейного принуждения.

### 21.2 Progression pillars

Прогресс должен идти через:

- исследование биомов;
- добычу материалов;
- крафт инструментов;
- активацию структур;
- победу над боссами;
- достижения;
- открытие рецептов;
- сюжетные записи;
- восстановление или искажение магических узлов.

### 21.3 Story system

Нужны системы:

```text
QuestDef
QuestState
Objective
Trigger
Reward
LoreEntry
WorldFlag
ProgressionGate
```

Квесты должны быть data-driven.

Типы objectives:

- visit biome;
- discover structure;
- collect item;
- craft item;
- activate altar;
- defeat mob/boss;
- survive night/event;
- restore node;
- open portal;
- read lore;
- build required multiblock structure.

### 21.4 Нелинейность

Игрок может:

- игнорировать историю и строить базу;
- исследовать мир;
- играть с друзьями;
- заниматься фермами/крафтом;
- ходить в данжи;
- постепенно открывать сюжет.

История не должна ломать sandbox. Она должна добавлять цели, но не запрещать свободную игру.

### 21.5 Achievements

Система достижений должна быть отдельной от story quests.

Нужны:

- achievement definitions;
- hidden achievements;
- multiplayer achievements;
- progression achievements;
- silly/funny achievements;
- rare exploration achievements.

Achievement examples:

```text
First Shelter
First Night Survived
Found a Whispering Grove
Opened the First Gate
Defeated a Forest Guardian
Built a Moving Bridge
Lit 100 Torches
Died to Your Own Ritual
Survived With 1 HP
Hosted a LAN World
```

### 21.6 World flags

Мир должен хранить глобальные флаги:

```text
first_portal_opened
forest_corruption_level
boss_1_defeated
moon_event_unlocked
ancient_gate_restored
deep_biome_access
```

Эти флаги влияют на:

- генерацию новых структур;
- доступность рецептов;
- музыку;
- освещение;
- мобов;
- события;
- торговлю/loot;
- прогресс достижений.

---

## 22. Meaningful world generation

Генерация должна быть не просто “шум + деревья”. У мира должен быть смысл.

### 22.1 Generation layers

Генерация делится на слои:

```text
base terrain
climate
biomes
caves
ores
water/lakes/rivers
vegetation
structures
magic/corruption
story landmarks
encounters
loot
```

### 22.2 Biome identity

Каждый биом должен иметь:

- свою палитру освещения;
- свой ambient sound;
- свои блоки;
- свои растения;
- своих мобов;
- свои структуры;
- свои ресурсы;
- свой gameplay hook.

Примеры биомов:

```text
Calm Plains
Old Forest
Whispering Grove
Ash Swamp
Crystal Caves
Moonlit Highlands
Sunken Ruins
Deep Root Tunnels
Black Pine Expanse
Fog Valley
```

### 22.3 Dark lighting direction

Нужен художественный стиль:

- не абсолютная темнота;
- контрастное сумрачное освещение;
- туман;
- мягкий bloom от магических блоков;
- холодные ночи;
- тёплые костры/факелы;
- биолюминесцентные растения;
- яркие магические акценты;
- шейдеры не должны ломать читаемость блоков.

### 22.4 Structure-driven exploration

Структуры должны создавать цели:

- башня видна издалека;
- руины содержат lore;
- алтарь требует предметы;
- портал требует multiblock activation;
- данж содержит босса;
- мост/ворота открывают новый маршрут;
- магический узел меняет биом вокруг.

### 22.5 Event generation

Мир должен поддерживать события:

- blood moon-like danger night, но с оригинальным названием;
- forest whisper event;
- meteor/crystal fall;
- traveling fog;
- corrupted rain;
- wandering trader-like event with original design;
- boss arena awakening.

События должны быть data-driven и сетево синхронизированы сервером.

---

## 23. Magic system

Нужна простая, но расширяемая магия.

### 23.1 Magic resources

Ввести:

- mana/energy optional;
- crystals;
- essence;
- runes;
- corrupted fragments;
- purified fragments.

### 23.2 Magic actions

Возможности:

- place rune;
- activate altar;
- open portal;
- enchant tool;
- light area;
- repel mobs;
- reveal hidden structure;
- grow magical tree;
- move structure part;
- create temporary bridge;
- purify/corrupt block area.

### 23.3 Magic architecture

```text
SpellDef
RitualDef
RuneDef
MagicEffect
AreaEffect
TimedEffect
WorldModifier
```

Магия должна работать через event/effect pipeline:

```text
input/action -> validation -> cost -> effect execution -> world/entity changes -> network replication -> audio/visual feedback
```

---

## 24. Codex self-correction loop

Codex должен работать по фазам и после каждой фазы сам себя проверять.

В конце каждой фазы Codex обязан:

1. Запустить:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run pyright` или выбранный type checker
2. Запустить игру/сервер в минимальном smoke test.
3. Обновить `README.md`.
4. Обновить `docs/PROGRESS.md`.
5. Обновить `docs/NEXT_STEPS.md`.
6. Добавить/обновить perf benchmark, если фаза затрагивает hot path.
7. Записать known issues.
8. Не переходить к следующей фазе, если текущая не запускается.

Файл `docs/PROGRESS.md` должен содержать:

```text
Current phase
Completed checklist
Failed checks
Performance notes
Known bugs
Next recommended tasks
```

Файл `docs/NEXT_STEPS.md` должен содержать маленький actionable backlog на 5–15 пунктов.

---


## 25. Testing strategy

### 25.1 Unit tests

Обязательно покрыть:

- block registry;
- item registry;
- recipes;
- inventory operations;
- chunk coordinate conversions;
- world seed determinism;
- DDA raycast;
- AABB collision;
- fluid propagation;
- light propagation;
- protocol encoding/decoding;
- save/load roundtrip.

### 25.2 Integration tests

- generate world, save, load, compare chunks;
- server starts, client connects, receives chunks;
- player breaks block, server validates, clients receive delta;
- inventory pickup/drop;
- mob spawn/update/despawn.

### 25.3 Performance tests

- meshing one chunk section;
- meshing 100 chunk sections;
- worldgen 100 chunks;
- render mock draw list building;
- protocol serialize/deserialize 1000 messages;
- server tick with 8 players and 200 mobs.

### 25.4 Golden tests

- deterministic terrain sample for fixed seed;
- deterministic structure placement;
- recipe registry snapshots;
- protocol compatibility snapshots.

---

## 26. Performance budgets

### 26.1 Frame budget at 60 FPS

Total frame: 16.6 ms.

Target:

```text
render submit:     <= 4 ms
chunk upload:      <= 2 ms average
client sim:        <= 2 ms
UI:                <= 1 ms
network handling:  <= 1 ms
misc:              <= 2 ms
GPU frame:         <= 12 ms medium settings
```

### 26.2 Server tick budget at 20 TPS

Total tick: 50 ms.

Target:

```text
players:           <= 3 ms
entities/mobs:     <= 10 ms
world updates:     <= 10 ms
chunks/load/save:  async/background
network:           <= 8 ms
margin:            rest
```

### 26.3 Chunk meshing

Targets:

```text
visible-face mesh 16^3 section: <= 2 ms average
greedy mesh 16^3 section:       <= 4 ms average
chunk upload to GPU:            amortized, not all at once
```

---

## 27. Development phases

## Phase 1 — Project skeleton

Checklist:

- [x] Create Python package `voxel_sandbox`.
- [x] Configure `pyproject.toml`.
- [x] Add Ruff.
- [x] Add Pyright or mypy.
- [x] Add pytest.
- [x] Add CLI entry point.
- [x] Add logging.
- [x] Add config loading.
- [x] Add primary no-argument game entry point.
- [x] Keep `server` and `client --connect` as developer/advanced commands.
- [x] Add dev README.
- [x] Add architecture decision records folder.

Done when:

- [x] `python -m voxel_sandbox --help` works.
- [x] Tests run.
- [x] Linter passes.
- [x] Empty client window can open.

---

## Phase 2 — OpenGL client shell

Checklist:

- [x] Create pyglet window.
- [x] Create ModernGL context.
- [x] Render clear color.
- [x] Implement camera.
- [x] Implement input system.
- [x] Implement fixed update loop + variable render loop.
- [x] Add debug overlay FPS/frame time.
- [x] Add shader loading.
- [x] Add hot reload shaders in dev mode.

Done when:

- [ ] Empty 3D scene runs at stable FPS.
- [x] Camera moves.
- [x] Debug overlay shows FPS.

---

## Phase 3 — Blocks and chunks

Checklist:

- [x] Implement BlockDef.
- [x] Implement BlockRegistry.
- [x] Implement ChunkCoord.
- [x] Implement SectionCoord.
- [x] Implement ChunkSection array storage.
- [x] Implement World interface.
- [x] Implement get/set block.
- [x] Implement dirty flags.
- [x] Add tests for coordinate conversion.
- [x] Add tests for block registry.
- [x] Add tests for chunk storage.

Done when:

- [x] Can create chunk.
- [x] Can set/get blocks.
- [x] Tests pass.

---

## Phase 4 — Basic meshing and rendering

Checklist:

- [x] Implement visible-face mesher.
- [x] Generate vertices/indices for chunk section.
- [x] Upload mesh to GPU.
- [x] Render opaque chunk mesh.
- [x] Implement texture atlas.
- [x] Add UV mapping.
- [x] Render grass/dirt/stone test chunk.
- [x] Add frustum culling.
- [x] Add mesh cache per chunk section.
- [x] Add benchmark for meshing.

Done when:

- [x] A chunk renders.
- [x] Only visible faces are meshed.
- [x] Camera can fly around.
- [x] Meshing benchmark exists.

---

## Phase 5 — Terrain generation

Checklist:

- [x] Add deterministic seed system.
- [x] Add noise-based heightmap.
- [x] Generate stone/dirt/grass.
- [x] Add trees.
- [x] Add ores.
- [x] Add caves.
- [x] Add biomes MVP.
- [x] Generate chunks around player.
- [x] Add background worker for worldgen.
- [x] Add chunk loading queue.
- [x] Add chunk unloading.
- [x] Add tests for deterministic generation.

Done when:

- [x] Player can fly over generated terrain.
- [x] Same seed creates same world.
- [x] Chunks stream around camera.

---

## Phase 6 — First-person player and collision

Checklist:

- [x] Implement player transform.
- [x] Implement gravity.
- [x] Implement AABB collision against blocks.
- [x] Implement walking.
- [x] Implement jumping.
- [x] Implement mouse look.
- [x] Implement DDA block raycast.
- [x] Implement block highlight.
- [x] Implement break block.
- [x] Implement place block.
- [x] Add tests for DDA.
- [x] Add tests for AABB collision.
- [x] Treat unloaded chunks and the lower world boundary as collision barriers.
- [x] Validate saved player positions and recover invalid positions at a safe spawn.
- [x] Add a smoke regression test for invalid-position recovery without inventory loss.

Done when:

- [x] Player walks on terrain.
- [x] Player cannot pass through blocks.
- [x] Player can break/place blocks.

---

## Phase 7 — Lighting MVP

Checklist:

- [x] Add sky light simple model.
- [x] Add block light array.
- [x] Add torch/light-emitting block (`Gloam Lantern`).
- [x] Add sky and block light values into mesh vertices.
- [x] Add smooth lighting option.
- [x] Add ambient occlusion option.
- [x] Add day/night color.
- [x] Add fog.
- [x] Add graphics settings toggles (`F6` smooth, `F7` AO, `F8` fog).

Done when:

- [x] Terrain has non-flat lighting.
- [x] Gloam Lantern emits visible warm light.
- [x] Fog hides far chunks.
- [x] Smooth lighting can be toggled.

---

## Phase 8 — Greedy meshing

Checklist:

- [x] Implement greedy meshing for opaque blocks.
- [x] Keep fallback visible-face meshing (`F9`).
- [x] Add benchmark comparison.
- [x] Ensure textures tile correctly.
- [x] Ensure lighting/AO constraints are respected.
- [x] Sample light/AO through neighboring section/chunk halo data.
- [x] Remove visible diagonal/cross-shaped smooth-light and AO artifacts.
- [x] Add debug mode to show mesh stats and active mesher.
- [x] Add chunk mesh triangle count overlay.
- [x] Move worldgen/lighting and section meshing to reusable process workers.
- [x] Limit completed chunk integration and GPU section uploads per frame.

Done when:

- [x] Triangle count drops significantly (`2048 -> 12` in the flat benchmark section).
- [x] Meshing stays inside the performance budget.
- [x] Visual artifacts are acceptable for the generated-texture prototype.
- [x] Section/chunk halo sampling does not create false zero-light borders.
- [x] Streaming render benchmark remains below the 16.6 ms frame budget.

---

## Phase 9 — Water

Checklist:

- [x] Add water block.
- [x] Add transparent render pass.
- [x] Add water shader.
- [x] Add animated UV/waves.
- [x] Add underwater fog.
- [x] Add fluid levels.
- [x] Add simple fluid propagation.
- [x] Add bucket-like item optional.
- [x] Add tests for fluid propagation.

Done when:

- [x] Water renders separately.
- [x] Water is transparent.
- [x] Water can flow in simple cases.

---

## Phase 10 — Inventory, items, crafting

Checklist:

- [x] Implement ItemDef.
- [x] Implement ItemRegistry.
- [x] Implement ItemStack.
- [x] Implement inventory grid.
- [x] Implement hotbar.
- [x] Implement item pickup.
- [x] Implement item drop.
- [x] Implement block drops.
- [x] Implement 2x2 crafting.
- [x] Implement 3x3 crafting.
- [x] Implement workbench block.
- [x] Implement recipes config.
- [x] Add tests for inventory.
- [x] Add tests for crafting.

Done when:

- [x] Player can collect drops.
- [x] Player can switch hotbar slot.
- [x] Player can craft basic items.

---

## Phase 11 — Entities and mobs

Visual scope note:

- Phase 11 validates ECS, gameplay, AI, combat and entity rendering only.
- Single-color cuboids are temporary proxy models, not finished mob art.
- Finished creature models, textures and moving body parts are mandatory in Phase 20.
- Visual references may guide quality and readability, but models, skins, silhouettes,
  animation clips and names must remain original and must not copy Minecraft or mod assets.

Checklist:

- [x] Implement EntityId.
- [x] Implement ECS-lite component storage.
- [x] Implement Transform component.
- [x] Implement Velocity component.
- [x] Implement Collider component.
- [x] Implement Health component.
- [x] Implement RenderModel component.
- [x] Implement MobAI component.
- [x] Implement item entities.
- [x] Implement passive mob.
- [x] Implement hostile mob.
- [x] Implement basic AI.
- [x] Implement spawn/despawn rules.
- [x] Implement damage.
- [x] Implement death/drops.
- [x] Add tests for ECS storage.
- [x] Add tests for mob state transitions.

Done when:

- [x] Items exist as entities.
- [x] Passive mob wanders.
- [x] Hostile mob chases player.
- [x] Mobs can die and drop items.

---

## Phase 12 — Save/load

Checklist:

- [x] Implement world metadata save.
- [x] Implement player save.
- [x] Implement chunk save.
- [x] Implement chunk load.
- [x] Add autosave.
- [x] Add dirty chunk tracking.
- [x] Add compression.
- [x] Add versioned format.
- [x] Add migration stub.
- [x] Add save/load tests.

Done when:

- [x] Modified world persists after restart.
- [x] Player inventory persists.
- [x] Save format version is stored.

---

## Phase 13 — Local multiplayer MVP

Checklist:

- [x] Implement protocol frame.
- [x] Implement msgpack payloads.
- [x] Implement TCP server.
- [x] Implement TCP client.
- [x] Implement handshake.
- [x] Implement join.
- [x] Server sends chunks.
- [x] Client renders received chunks.
- [x] Client sends input.
- [x] Server updates player state.
- [x] Server sends entity snapshots.
- [x] Implement block action replication.
- [x] Implement chat.
- [x] Add integration test for client/server.

Done when:

- [x] Two clients can join LAN server.
- [x] Players see each other.
- [x] Block changes replicate.
- [x] Chat works.

---

## Phase 14 — Multiplayer polish

Checklist:

- [x] Add client prediction.
- [x] Add interpolation.
- [x] Add server reconciliation.
- [x] Add delta snapshots.
- [x] Add chunk interest management.
- [x] Add entity interest management.
- [x] Add rate limiting.
- [x] Add disconnect/reconnect handling.
- [x] Add LAN discovery.
- [x] Add Open to LAN flow in the singleplayer Pause Menu.
- [x] Add join LAN menu.
- [x] Add nickname selection.
- [x] Add Direct Connect address input.
- [x] Add multiplayer chat input.
- [x] Run singleplayer through the in-process authoritative server.

Done when:

- [x] Movement feels okay over LAN.
- [x] Joining via LAN list works.
- [x] Server handles 8 players in perf test.

---

## Phase 15 — Shadows and shader polish

Checklist:

- [x] Add shadow map framebuffer.
- [x] Add sun light matrix.
- [x] Render world depth to shadow map.
- [x] Apply shadows in chunk shader.
- [x] Add entity shadows.
- [x] Add shadow bias tuning.
- [x] Add PCF filtering.
- [x] Keep the shadow depth pass and filtering inside the GPU frame budget.
- [x] Add shadow quality settings.
- [x] Add water shader polish.
- [x] Add skybox/sun/moon.
- [x] Add clouds.
- [x] Add postprocess optional.

Done when:

- [x] Shadows can be enabled.
- [x] FPS remains acceptable on medium.
- [x] Medium shadow settings keep GPU frame at or below the `<= 12 ms` target scene budget.
- [x] Low settings can disable shadows.

---

## Phase 16 — Structures and world richness

Checklist:

- [x] Add structure template format.
- [x] Add deterministic placement.
- [x] Add collision with terrain.
- [x] Add structure loot tables.
- [x] Add ruins.
- [x] Add camps.
- [x] Add caves with resources.
- [x] Add rare landmarks.
- [x] Add debug structure viewer.
- [x] Add tests for deterministic placement.

Done when:

- [x] World contains interesting generated structures.
- [x] Same seed places same structures.

---

## Phase 17 — UI polish and settings

Checklist:

- [x] Main menu.
- [x] Create world menu.
- [x] Load world menu.
- [x] Open to LAN action in the singleplayer Pause Menu.
- [x] Join LAN menu.
- [x] Settings menu.
- [x] Controls menu.
- [x] Inventory UI.
- [x] Crafting UI.
- [x] Pause menu.
- [x] Debug overlay.
- [x] Key rebinding.
- [x] Persist settings.

Done when:

- [x] Game can be used without CLI.
- [x] Settings persist across restarts.

---

## Phase 18 — Packaging

Checklist:

- [x] Add icon.
- [x] Add version.
- [x] Add build script.
- [x] Package with PyInstaller or Briefcase.
- [x] Test Windows build.
- [x] Test macOS build.
- [x] Test Linux build optional.
- [x] Include assets.
- [x] Include shader files.
- [x] Add crash logs.
- [x] Add first-run config.

Done when:

- [x] Game launches from packaged build.
- [x] Assets and shaders are found.
- [x] Saves are written to user data dir.

Native Windows, macOS, and Linux package jobs passed in GitHub Actions run `27496080787`.

---


## 27.1 Expanded creative backlog phases

Эти фазы идут после технического MVP, но архитектурно должны учитываться заранее.

### Phase 19 — Audio foundation

Checklist:

- [x] Add AudioBackend protocol.
- [x] Add PygletAudioBackend.
- [x] Add NullAudioBackend for tests/server.
- [x] Add audio event bus.
- [x] Add sound registry.
- [x] Add music registry.
- [x] Add volume groups.
- [x] Add positional block sounds.
- [x] Add player footstep sounds by block material.
- [x] Add mob sound hooks.
- [x] Add biome ambience loop.
- [x] Add music director state machine.
- [x] Add settings UI for audio volumes.
- [x] Add tests for audio event routing with NullAudioBackend.

Done when:

- [x] Blocks, UI and mobs can trigger sounds.
- [x] Biomes can change ambience.
- [x] Music can change by game state.
- [x] Server runs with NullAudioBackend.

### Phase 20 — Articulated mobs and procedural animation

Checklist:

- [x] Add original mob texture/skin format and texture atlas support.
- [x] Add per-model-part UV/material definitions.
- [x] Add model part/skeleton definition format.
- [x] Add AnimationClip format.
- [x] Add AnimationGraph.
- [x] Add Pose/PoseBlender.
- [x] Add procedural motion controllers.
- [x] Add head look-at controller.
- [x] Add limb swing controller.
- [x] Add tail/tentacle wave controller.
- [x] Add flying wing controller.
- [x] Add crawling gait controller.
- [x] Add animation network replication state.
- [x] Convert passive mob to articulated model.
- [x] Convert hostile mob to articulated model.
- [x] Give passive and hostile mobs distinct original silhouettes, palettes and proportions.
- [x] Add idle breathing/bobbing and speed-synchronized walk/run cycles.
- [x] Add attack wind-up/release/recover, hurt reaction and death animation.
- [x] Animate head, torso and limbs independently instead of moving one rigid cuboid.
- [x] Add entity animation culling/LOD or batching to stay inside the entity frame budget.
- [x] Add rendered animation smoke/visual regression coverage.
- [x] Add animation debug overlay.

Done when:

- [x] Mobs have moving body parts.
- [x] Passive and hostile mobs no longer use single-color proxy cuboids.
- [x] Both mobs have original textured articulated models readable at gameplay distance.
- [x] Walk, attack, hurt and death states have visibly different poses/motion.
- [x] New movement style can be added without rewriting renderer.
- [x] Multiplayer clients see consistent animation phases.

### Phase 20.1 — Difficulty, light-aware hostile spawning and command line

Checklist:

- [x] Add persisted `peaceful` and `normal` gameplay difficulty settings.
- [x] Expose difficulty in the in-game Settings screen.
- [x] Remove existing hostile mobs immediately when peaceful difficulty is selected.
- [x] Reduce normal hostile population to one nearby mob and evaluate replenishment every 5 seconds.
- [x] Prevent hostile spawning above configurable effective light level 7.
- [x] Combine day-adjusted skylight and block light for hostile spawn checks.
- [x] Reject spawn candidates whose chunks are not loaded.
- [x] Add an in-game command line on `/` with `/help`.
- [x] Add `/time set day|noon|night|midnight|<ticks>`.
- [x] Add `/difficulty peaceful|normal`.
- [x] Add unit and OpenGL integration coverage for settings, light, spawning and commands.

Done when:

- [x] Peaceful gameplay contains no aggressive mobs.
- [x] Normal daytime does not spawn aggressive mobs in well-lit locations.
- [x] Normal mode can spawn an aggressive mob in darkness or at night.
- [x] Time and difficulty can be changed without leaving the world.

### Phase 20.2 — Gameplay presentation quality recovery

This corrective phase is mandatory before Phase 21. Broad visual references may guide readability
and interaction conventions, but textures, sounds, models and code must remain original and must
not copy Minecraft, shader-pack or mod assets.

Checklist:

- [x] Replace noisy full-image mob texturing with original per-part 4x4 material sheets.
- [x] Use a readable blocky cow silhouette for the passive mob and zombie silhouette for hostile.
- [x] Add per-part UV regions so faces, bodies, limbs and feet use intentional materials.
- [x] Add joint pivots and inherited parent rotation for stable limb/head/tail animation.
- [x] Correct entity yaw so models face their actual movement direction.
- [x] Add mob vertical velocity, gravity, voxel-floor landing and water buoyancy.
- [x] Render entities between opaque terrain and transparent water.
- [x] Reduce water opacity and improve underwater visibility.
- [x] Replace text-list hotbar/inventory with large square slots, icons and corner stack counts.
- [x] Add interactive 2x2/3x3 crafting grids and a dedicated recipe output slot.
- [x] Return remaining crafting/cursor items safely when inventory closes.
- [x] Move chat/command entry and visible command responses to the lower-left HUD.
- [x] Keep the detailed debug overlay hidden by default and toggle it with `F3`.
- [x] Raise cave ambient floor and soften shadow/AO darkness without removing light gameplay.
- [x] Replace single-tone mob effects with distinct normalized cow/zombie sounds.
- [x] Add per-resource audio gain staging and quieter default effects/music/ambience balance.
- [x] Add unit, hidden-window OpenGL and waveform normalization coverage.

Done when:

- [x] Cow and zombie materials are recognizable and no body part samples the full texture sheet.
- [x] Mobs fall from ledges, land on blocks and rise rather than disappear when submerged.
- [x] Water transparently overlays visible entities instead of masking them through depth writes.
- [x] Inventory and crafting can be understood from slots/icons without reading item-list strings.
- [x] `/help` and other command responses are visible while the inventory is closed.
- [x] Unlit caves remain dark but geometry is still readable.
- [x] Gameplay effects remain below clipping and are gain-balanced by semantic category.

### Phase 21 — Moving structures and magical machines

Checklist:

- [ ] Add BlockEntity system.
- [ ] Add MultiBlockStructure definition.
- [ ] Add StructureEntity runtime state.
- [ ] Add animated render parts.
- [ ] Add collision phase updates.
- [ ] Add save/load for structure state.
- [ ] Add network replication for structure state.
- [ ] Implement opening stone gate.
- [ ] Implement rotating altar.
- [ ] Implement moving platform or bridge.
- [ ] Add debug commands for spawning structures.
- [ ] Add tests for structure state machines.

Done when:

- [ ] At least 3 interactive structures work.
- [ ] Structures animate without rebuilding thousands of blocks each frame.
- [ ] Structure state persists and replicates over LAN.

### Phase 22 — Story progression foundation

Checklist:

- [ ] Add QuestDef.
- [ ] Add Objective system.
- [ ] Add Trigger system.
- [ ] Add Reward system.
- [ ] Add LoreEntry registry.
- [ ] Add WorldFlag storage.
- [ ] Add ProgressionGate.
- [ ] Add quest journal UI.
- [ ] Add discovery notifications.
- [ ] Add multiplayer-safe progression events.
- [ ] Add first story chain.
- [ ] Add tests for quest progress and world flags.

Done when:

- [ ] Player can discover a structure and receive story progress.
- [ ] Quest state persists.
- [ ] LAN players share world-level progression.

### Phase 23 — Achievements

Checklist:

- [ ] Add AchievementDef.
- [ ] Add AchievementState.
- [ ] Add hidden achievements.
- [ ] Add achievement triggers.
- [ ] Add UI toast notification.
- [ ] Add achievements screen.
- [ ] Add per-player achievements.
- [ ] Add world achievements optional.
- [ ] Add multiplayer achievements.
- [ ] Add tests for achievement triggers.

Done when:

- [ ] Achievements unlock reliably.
- [ ] Achievements persist.
- [ ] Multiplayer achievements work without duplicate spam.

### Phase 24 — Meaningful biomes and dark magic generation

Checklist:

- [ ] Add biome ambience metadata.
- [ ] Add biome lighting metadata.
- [ ] Add biome fog metadata.
- [ ] Add biome-specific mob spawns.
- [ ] Add biome-specific structures.
- [ ] Add magic/corruption generation layer.
- [ ] Add story landmark placement.
- [ ] Add biome progression gates.
- [ ] Add at least 5 distinct biomes.
- [ ] Add at least 3 rare landmarks.
- [ ] Add tests for deterministic biome/story placement.

Done when:

- [ ] Biomes feel different visually and mechanically.
- [ ] Exploration has meaningful goals.
- [ ] Same seed generates same landmarks.

### Phase 25 — Magic and rituals

Checklist:

- [ ] Add MagicEffect pipeline.
- [ ] Add SpellDef.
- [ ] Add RitualDef.
- [ ] Add RuneDef.
- [ ] Add altar activation.
- [ ] Add area effects.
- [ ] Add timed effects.
- [ ] Add world modifiers.
- [ ] Add magic particles.
- [ ] Add magic sounds.
- [ ] Add ritual UI feedback.
- [ ] Add multiplayer validation.
- [ ] Add tests for magic effects.

Done when:

- [ ] Players can perform at least 3 rituals.
- [ ] Magic can affect blocks/entities.
- [ ] Magic effects replicate over LAN.

### Phase 26 — Co-op adventure loop

Checklist:

- [ ] Add co-op objectives.
- [ ] Add boss arena trigger.
- [ ] Add boss phase system.
- [ ] Add shared loot chest/reward.
- [ ] Add party-safe respawn near event.
- [ ] Add danger music state.
- [ ] Add event completion world flag.
- [ ] Add difficulty scaling by player count.
- [ ] Add first complete adventure arc.

Done when:

- [ ] Friends can host LAN and complete a small story arc.
- [ ] Arc includes exploration, crafting/prep, structure activation, fight/event and reward.
- [ ] Sandbox remains playable after arc completion.


## 28. Definition of Done for full game

Full game is done when:

- [ ] Client launches from menu.
- [ ] Singleplayer works.
- [ ] Open to LAN works from a running singleplayer world.
- [ ] Join LAN works.
- [ ] Procedural world streams around player.
- [ ] Player can mine/place blocks.
- [ ] Inventory works.
- [ ] Crafting works.
- [ ] Tools work.
- [ ] Basic combat works.
- [ ] Passive mobs exist.
- [ ] Hostile mobs exist.
- [ ] Water exists and flows simply.
- [ ] Lighting works.
- [ ] Shadows work.
- [ ] Settings work.
- [ ] Save/load works.
- [ ] Structures generate.
- [ ] Interactive/moving structures work.
- [ ] Mobs support articulated/procedural animations.
- [ ] Sounds, ambience and music work.
- [ ] Story progression works.
- [ ] Achievements work.
- [ ] Magic/ritual system works.
- [ ] Meaningful dark-magic biomes exist.
- [ ] Debug overlay exists.
- [ ] Tests pass.
- [ ] Perf benchmarks pass.
- [ ] Medium laptop reaches target FPS on medium settings.
- [ ] Low settings are playable on weaker machine.

---

## 29. Suggested milestones for Codex

Do not implement everything in one PR.

Milestone order:

1. Skeleton + window.
2. Chunks + basic rendering.
3. Terrain streaming.
4. Player movement + collisions.
5. Block interaction.
6. Lighting.
7. Greedy meshing.
8. Inventory/crafting.
9. Save/load.
10. Network MVP.
11. Entities/mobs.
12. Water.
13. Shadows.
14. UI/settings.
15. Structures.
16. Packaging/perf polish.
17. Audio foundation.
18. Articulated mobs.
19. Moving structures.
20. Story progression.
21. Achievements.
22. Dark magic biomes.
23. Magic/rituals.
24. Co-op adventure loop.

Each milestone must:

- add tests;
- add profiling notes;
- update README;
- avoid giant files;
- keep render hot path clean.

---

## 30. Coding standards

### 30.1 Python

Use:

- `dataclasses` with `slots=True` for small immutable configs;
- `typing.Protocol` for boundaries;
- `numpy` arrays in hot data paths;
- explicit coordinate types;
- small modules;
- no global mutable registries except bootstrapped read-only registries.

Avoid:

- huge inheritance trees;
- per-block objects;
- dynamic reflection in hot paths;
- service locator pattern;
- hidden global state;
- circular imports.

### 30.2 Style

- Ruff format.
- 100–120 char max line.
- Type hints everywhere in application/domain code.
- Hot paths may use lower-level optimized style with clear comments.

---

## 31. Suggested module contracts

### 31.1 World

```python
class World(Protocol):
    def get_block(self, x: int, y: int, z: int) -> int: ...
    def set_block(self, x: int, y: int, z: int, block_id: int) -> None: ...
    def get_chunk(self, cx: int, cz: int) -> Chunk | None: ...
```

### 31.2 Mesher

```python
class ChunkMesher(Protocol):
    def build_section_mesh(
        self,
        world_view: WorldView,
        section_coord: SectionCoord,
    ) -> MeshData: ...
```

### 31.3 Renderer

```python
class Renderer(Protocol):
    def upload_chunk_mesh(self, key: SectionKey, mesh: MeshData) -> None: ...
    def remove_chunk_mesh(self, key: SectionKey) -> None: ...
    def render_frame(self, frame: RenderFrame) -> None: ...
```

### 31.4 Network

```python
class GameServer(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

class GameClient(Protocol):
    async def connect(self, address: str, port: int) -> None: ...
    async def disconnect(self) -> None: ...
```

---

## 32. Debug tools

Add debug overlay:

- FPS;
- frame time;
- GPU time if available;
- player position;
- chunk coord;
- loaded chunks;
- visible chunks;
- rendered triangles;
- draw calls;
- mesh queue size;
- worldgen queue size;
- network ping;
- server tick time;
- entity count;
- mob count.

Add debug commands:

```text
/tp x y z
/give item count
/time set day
/spawn mob
/chunkstats
/reloadshaders
/reloadassets
/seed
```

---

## 33. Risks and mitigations

### Risk: Python too slow for full voxel engine

Mitigation:

- GPU rendering;
- chunk meshes;
- NumPy arrays;
- greedy meshing;
- background workers;
- profile early;
- move only hot parts to Numba/Cython if needed.

### Risk: Network desync

Mitigation:

- server authority;
- deterministic server state;
- sequence numbers;
- reconciliation;
- integration tests.

### Risk: Architecture overengineering

Mitigation:

- clean boundaries only at module/service level;
- data-oriented hot loops;
- no DI in hot paths.

### Risk: macOS OpenGL limitations

Mitigation:

- target OpenGL 3.3 core profile;
- avoid exotic extensions;
- test early on macOS;
- keep shader versions compatible.

### Risk: Scope explosion

Mitigation:

- MVP first;
- feature flags;
- backlog priorities;
- no “all features before playable”.

---


## 33.1 Git workflow, phase commits and rollback safety

Codex должен использовать Git как обязательный механизм сохранения прогресса.

Главная цель:

> После каждого завершённого пункта чеклиста или маленькой логической группы изменений должен быть рабочий коммит, к которому можно откатиться.

Нельзя работать огромными несохранёнными пачками. Нельзя делать один гигантский коммит на всю фазу.

### 33.1.1 Repository initialization

В Phase 1 обязательно:

- [x] Проверить, есть ли `.git`.
- [x] Если `.git` нет — выполнить `git init`.
- [x] Создать `.gitignore`.
- [x] Добавить в `.gitignore`:
  - `.venv/`
  - `.pytest_cache/`
  - `.ruff_cache/`
  - `.mypy_cache/`
  - `.pyright/`
  - `__pycache__/`
  - `*.pyc`
  - build artifacts
  - local saves
  - local logs
  - generated profiling dumps
  - OS junk files.
- [x] Сделать первый phase-коммит с каркасом проекта.

Первый коммит:

```bash
git add .
git commit -m "phase-01: initialize uv project skeleton"
```

### 33.1.2 Commit frequency

Codex должен коммитить:

- после каждого завершённого checklist item, если он достаточно самостоятельный;
- после маленькой группы связанных пунктов, если отдельно они не имеют смысла;
- после каждого зелёного тестируемого milestone внутри фазы;
- перед рискованным рефакторингом;
- после успешного рефакторинга;
- перед переходом к следующей фазе.

Размер коммита:

- идеальный коммит: 1 логическая мысль;
- допустимо: 2–5 тесно связанных checklist items;
- плохо: вся фаза одним коммитом;
- запрещено: несколько фаз одним коммитом.

### 33.1.3 Commit message format

Формат commit message:

```text
phase-XX.item-YY: short imperative summary
```

Примеры:

```text
phase-01.item-01: initialize uv project metadata
phase-01.item-02: add ruff pytest and pyright config
phase-02.item-01: create pyglet window and render loop
phase-02.item-02: add first person camera controls
phase-03.item-04: implement chunk coordinate conversion
phase-04.item-03: render visible faces for chunk sections
phase-13.item-06: replicate block updates to clients
phase-20.item-02: add animation graph and pose blending
```

Если пункт охватывает несколько checklist entries:

```text
phase-04.items-02-04: upload section meshes to gpu
```

Для исправлений:

```text
fix.phase-04.item-03: correct uv mapping for side faces
test.phase-06.item-10: cover voxel dda edge cases
perf.phase-08.item-02: reduce greedy meshing allocations
refactor.phase-13.item-04: split protocol frame encoder
docs.phase-24.item-05: update biome generation notes
```

### 33.1.4 Required checks before every commit

Перед каждым коммитом Codex обязан выполнить минимальные проверки.

Базовые проверки:

```bash
uv run ruff check .
uv run pytest
```

Если проект уже настроил type checker:

```bash
uv run pyright
```

Если изменение затрагивает форматирование:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

Если изменение затрагивает hot path:

```bash
uv run python -m voxel_sandbox benchmark-mesher
```

или соответствующий benchmark:

```bash
uv run python -m voxel_sandbox benchmark-worldgen
uv run python -m voxel_sandbox benchmark-lighting
uv run python -m voxel_sandbox benchmark-network
```

Если изменение затрагивает клиент:

- запустить smoke test клиента;
- убедиться, что окно открывается;
- убедиться, что приложение не падает на старте.

Если изменение затрагивает сервер:

- запустить smoke test сервера;
- убедиться, что сервер стартует и корректно останавливается.

Коммит засчитывается только если:

- [ ] tests pass;
- [ ] lint pass;
- [ ] type check pass, если включён;
- [ ] smoke test pass, если применимо;
- [ ] README/docs обновлены, если изменился workflow;
- [ ] `docs/PROGRESS.md` обновлён;
- [ ] `docs/NEXT_STEPS.md` обновлён при переходе между задачами.

### 33.1.5 No broken commits rule

Запрещено коммитить:

- код, который не запускается;
- красные тесты;
- временные debug hacks;
- закомментированные большие куски старого кода;
- локальные save files;
- профилировочные dumps;
- ассеты-заглушки из чужих игр;
- `.venv`;
- generated cache files;
- broken shader files, если клиент из-за них падает.

Исключение:

Можно сделать временный WIP-коммит только если Codex явно находится в аварийной ситуации и нужно сохранить работу перед большим откатом. Такой коммит должен называться:

```text
wip.phase-XX: temporary checkpoint before rollback
```

Но перед продолжением Codex должен привести проект в зелёное состояние и сделать нормальный коммит. В финальном состоянии WIP-коммитов желательно не оставлять, если есть возможность сделать squash/rebase.

### 33.1.6 Branch strategy

Минимальная стратегия:

```text
main
  stable, запускаемый проект
```

Для больших фаз можно использовать ветки:

```text
phase/01-skeleton
phase/02-render-shell
phase/03-chunks
phase/04-meshing
phase/13-network-mvp
phase/20-articulated-mobs
```

Правило:

- `main` всегда должен быть рабочим;
- фазовая ветка может содержать промежуточные коммиты;
- перед merge в `main` все проверки должны быть зелёными;
- merge commit или fast-forward допустимы;
- история должна оставаться читаемой.

Если Codex работает один локально, можно коммитить прямо в `main`, но всё равно маленькими рабочими коммитами.

### 33.1.7 Progress tracking in docs

После каждого коммита Codex должен при необходимости обновлять `docs/PROGRESS.md`.

Формат записи:

```text
## Phase XX — Name

### Completed
- [x] item-YY: what was implemented
  - commit: <short-hash> <commit-message>
  - checks: pytest, ruff, pyright
  - notes: short note

### In progress
- [ ] item-ZZ: next task

### Known issues
- issue description or "None"

### Performance notes
- benchmark result or "Not applicable"
```

`docs/NEXT_STEPS.md` должен содержать следующий маленький план:

```text
# Next steps

1. phase-XX.item-YY: ...
2. phase-XX.item-ZZ: ...
3. ...
```

### 33.1.8 Commit checklist template

Перед каждым коммитом Codex должен мысленно пройти этот checklist:

```text
- [ ] Изменение маленькое и логически цельное.
- [ ] Код запускается.
- [ ] Тесты добавлены или обновлены.
- [ ] uv run pytest проходит.
- [ ] uv run ruff check . проходит.
- [ ] uv run pyright проходит, если включён.
- [ ] Smoke test пройден, если изменение затронуло client/server.
- [ ] Benchmark обновлён/запущен, если изменение затронуло performance hot path.
- [ ] docs/PROGRESS.md обновлён.
- [ ] docs/NEXT_STEPS.md обновлён, если изменился следующий план.
- [ ] git diff просмотрен.
- [ ] git status не содержит мусора.
- [ ] commit message соответствует формату.
```

Команды:

```bash
git status
git diff
uv run ruff check .
uv run pytest
uv run pyright
git add .
git commit -m "phase-XX.item-YY: short summary"
git status
```

### 33.1.9 Rollback rules

Если после изменения проект сломался и быстро исправить нельзя:

1. Посмотреть текущий diff:

```bash
git diff
git status
```

2. Попробовать точечно откатить проблемный файл:

```bash
git restore path/to/file.py
```

3. Если сломана вся попытка — откатиться к последнему рабочему коммиту:

```bash
git reset --hard HEAD
```

4. Если плохой коммит уже сделан:

```bash
git revert <commit-hash>
```

Не использовать `git reset --hard` на опубликованной/shared истории без явной необходимости.

### 33.1.10 Tags for stable milestones

После завершения каждой крупной фазы Codex должен создать tag:

```bash
git tag phase-01-complete
git tag phase-02-complete
git tag phase-03-complete
```

Перед tag обязательны:

```bash
uv run ruff check .
uv run pytest
uv run pyright
```

Если есть smoke tests/benchmarks для фазы — их тоже запустить.

### 33.1.11 Definition of committed done

Checklist item считается завершённым только если:

- [ ] код реализован;
- [ ] есть тест или обоснование, почему тест не нужен;
- [ ] проверки зелёные;
- [ ] документация обновлена при необходимости;
- [ ] изменения закоммичены;
- [ ] commit message содержит phase/item;
- [ ] `docs/PROGRESS.md` ссылается на коммит.

Если пункт не закоммичен — он не считается завершённым.


## 34. Hard rules for Codex

1. Never create one Python object per block.
2. Never render one block per draw call.
3. Never recalculate all chunks every frame.
4. Never put DI container into render/meshing loops.
5. Never block render thread on worldgen or disk IO.
6. Never trust client for authoritative world changes.
7. Never copy Minecraft assets.
8. Never add a feature without a minimal test or debug path.
9. Never optimize blindly; add benchmark/profiling first.
10. Never merge a milestone if the game does not launch.
11. Always use `uv` commands in docs, tests and developer workflows.
12. After each phase, update `docs/PROGRESS.md` and `docs/NEXT_STEPS.md`.
13. Keep gameplay systems data-driven when possible.
14. Use Git from Phase 1 onward.
15. Commit every completed checklist item or small logical group.
16. Never count a checklist item as done until it is tested, checked and committed.
17. Use commit messages with phase/item numbers.
18. Keep `main` in a runnable state.

---

## 35. First concrete task for Codex

Start with this exact first task:

> Create the project skeleton for `voxel_sandbox` with Python 3.12+, `pyproject.toml`, Ruff, pytest,
> a primary player entry point `uv run python -m voxel_sandbox`, a Main Menu shell, a pyglet +
> ModernGL client window, developer commands `server` and `client --connect`, a basic debug overlay
> showing FPS/frame time, and an empty render loop with a movable first-person camera. Do not implement
> chunks yet. Singleplayer must be designed to run through a local in-process authoritative server.

Acceptance criteria:

- [x] `uv run python -m voxel_sandbox` opens the game application and Main Menu.
- [x] Developer command `uv run python -m voxel_sandbox client --connect ...` opens a client window.
- [x] Mouse look and WASD camera movement work.
- [x] FPS is displayed.
- [x] Developer command `uv run python -m voxel_sandbox server` starts a placeholder server loop.
- [x] `pytest` passes.
- [x] `ruff check .` passes.
- [x] README explains how to run.
- [x] Git repository is initialized if it did not exist.
- [x] `.gitignore` exists and excludes caches, `.venv`, logs, saves and build artifacts.
- [x] Each completed checklist group is committed with `phase-01.item-XX` messages.
- [x] `docs/PROGRESS.md` and `docs/NEXT_STEPS.md` exist.

---

## 36. Second concrete task for Codex

After Phase 1 is done:

> Implement chunk storage and render one generated chunk section using visible-face meshing. Use NumPy storage, ModernGL VBO/IBO upload, a texture atlas, and a simple GLSL shader. Add tests for coordinate conversion and chunk get/set. Add a meshing benchmark.

Acceptance criteria:

- [x] One chunk section renders.
- [x] Only visible faces are generated.
- [x] Texture atlas works.
- [x] Mesh benchmark prints timings.
- [x] Tests pass.

---

## 37. Quality bar

This project should feel like a serious indie engine prototype, not a tutorial clone.

Priorities:

1. stable architecture;
2. playable MVP;
3. performance;
4. network correctness;
5. visual polish;
6. feature completeness.

Do not sacrifice FPS and architecture for adding many half-broken mechanics.
