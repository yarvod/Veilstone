# Veilstone — Рабочий план

## Overview

Рефакторинг архитектуры + исправление багов + расширяемость движка + поддержка ресурспаков.
Цель: сделать проект расширяемым для добавления новых фич (блоки, биомы, мобы, измерения, текстуры).

---

## Phase 0: Critical Engine Bugs ✅

### 0.1 Water Physics ✅
- [x] Игрок не может плавать — добавлен buoyancy, swim_speed, in_water
- [x] Вода не течёт — добавлен drain, horizontal spread with decay
- [x] Нельзя ломать блоки сквозь воду — raycast skip_block для fluids

### 0.2 Mob AI & Physics ✅
- [x] Мобы застревают в воде — smooth buoyancy с lerp
- [x] Мобы спавнятся внутри блоков — проверка 2-block clearance
- [x] AI не обходит препятствия — попытка 45°/90° поворота перед разворотом
- [x] Зомби бьёт игрока сквозь высоту — проверка abs(dy) <= 2.0

### 0.3 Combat & Animation ✅
- [x] Анимация удара зомби — state_phase сбрасывается при каждом ударе
- [x] Высотная проверка атаки — зомби не бьёт если игрок >2 блока выше

---

## Phase 1: Extract GameWindow God Class ✅

### 1.1 InventoryController ✅
- [x] Извлечь draw_hotbar, draw_health, draw_inventory
- [x] Извлечь crafting_*, inventory_slot_*, handle_crafting_click
- [x] Тесты: unit + integration

### 1.2 InputHandler ✅
- [x] Извлечь on_key_press, on_mouse_*, on_text, on_scroll
- [x] Тесты: unit (42 теста)

### 1.3 NetworkController ✅
- [x] Извлечь connect_remote, process_network_*, sync_remote_*
- [x] Извлечь lan_*, open_to_lan, _send_block_action
- [x] Тесты: unit (33 теста)

### 1.4 WorldManager ✅
- [x] Извлечь create_world, load_world, switch_world, save_player
- [x] Player position helpers (restore, validate, move_to_spawn)
- [ ] Тесты: unit

### 1.5 GameplayController ✅
- [x] Извлечь maintain_population, execute_command, _set_difficulty
- [x] match/case dispatch вместо 80-строчного if/elif chain
- [ ] Тесты: unit

### 1.6 Slim GameWindow ✅
- [x] Extract MenuUI → render/menu_ui.py
- [x] Extract HudController → render/hud_controller.py
- [x] apply_rebind → InputHandler; toggle_structure → NetworkController
- [x] Dead profiling code removed
- [x] window.py: 2614 → 579 строк
- [x] Integration тесты (311/311)

---

## Phase 2: Data-Driven Content ✅

### 2.1 Blocks from TOML ✅
- [x] `data/blocks.toml` — определения блоков
- [x] `load_block_registry_from_toml()` — загрузка из файла
- [x] Тесты: unit (3 теста)

### 2.2 Biomes from TOML ✅
- [x] `data/biomes.toml` — параметры биомов
- [x] `BiomeDef` + `BiomeRegistry` в domain/biomes/
- [x] Тесты: unit (7 тестов)

### 2.3 Items from TOML ✅
- [x] `data/items.toml` — определения предметов + drop table
- [x] `load_item_registry_from_toml()` — загрузка из файла
- [x] Тесты: unit (2 теста)

---

## Phase T: Minecraft-style Texture Pack System (MVP)

Цель: Veilstone напрямую использует Minecraft Java-compatible resource pack layout.
Пользователь кладёт ZIP/папку в `resource_packs/`, выбирает через UI, применяет без рестарта.

**Ключевой принцип:** Не делать mapping layer как основной путь. Minecraft-style resource locations — основная система текстур. `data/blocks.toml` хранит texture IDs в формате `minecraft:block/name` напрямую.

**Целевой пак для ручного тестирования:** `resource_packs/Faithful-32x-1.21.11/` (уже распакован).

### Правила: ассеты и лицензии
- Не коммитить пользовательские паки и кеш атласов
- `.gitignore`: `resource_packs/*`, `!resource_packs/README.md`, `saves/texture_cache/`
- Veilstone только поддерживает структуру — не распространяет чужие ассеты

### MVP поддерживает
- `pack.mcmeta`; ZIP и folder packs; `assets/minecraft/textures/block/*.png`
- texture IDs в формате `minecraft:block/name`; block textures only
- первый кадр для animated strips; fallback на default/generated texture

### MVP не поддерживает
Кастомные `veilstone:*` блоки, blockstates, JSON models, items, entities, biome colormaps, полноценную анимацию.

---

### T1 — Convert block texture IDs ✅
- [x] `resource_packs/README.md`, `.gitignore` правила, пустой пакет `render/texture_packs/`
- [x] Обновить `data/blocks.toml`: все `texture_top/side/bottom` перевести на `minecraft:block/*`
- [x] Временные замены для Veilstone-specific блоков:
  - `veilwood_cut` → `minecraft:block/oak_log_top`
  - `veilwood_bark` → `minecraft:block/oak_log`
  - `veilwood_leaves` → `minecraft:block/oak_leaves`
  - `veilwood_planks` → `minecraft:block/oak_planks`
  - `dusk_crystal_ore` → `minecraft:block/diamond_ore`
  - `gloam_lantern` → `minecraft:block/lantern`
  - `runecraft_top` → `minecraft:block/crafting_table_top`
  - `runecraft_side` → `minecraft:block/crafting_table_side`
  - `glowing_mushroom` → `minecraft:block/red_mushroom`
  - `fireflies` → `minecraft:block/glow_lichen`
  - `water` → `minecraft:block/water_still`
- [x] Обновить generated atlas keys на те же `minecraft:block/*` IDs

Acceptance: default atlas работает; все texture IDs из `blocks.toml` резолюятся в UV.

---

### T2 — Resource location resolver ✅
Добавить resolver в `render/texture_packs/`:

```python
def resource_location_to_texture_path(resource: str) -> str:
    # "minecraft:block/stone" -> "assets/minecraft/textures/block/stone.png"
```

Правила:
- формат: `<namespace>:<kind>/<name>`
- MVP: поддержать `kind == "block"`; любой namespace уже работает автоматически
- invalid IDs дают понятную ошибку
- missing textures не крашат — уходят в fallback

Новые/обновлённые тесты:
- [x] `minecraft:block/stone` → `assets/minecraft/textures/block/stone.png`
- [x] Невалидный ID → ValueError с понятным сообщением
- [x] Folder и ZIP пак читаются через resolver

Acceptance: `uv run pytest -m unit`

---

### T3 — Minecraft Java pack reader ✅
- [x] Читать ZIP и folder packs
- [x] Проверять `pack.mcmeta`
- [x] `height > width and height % width == 0` → animated strip, брать первый кадр
- [x] Конвертировать PNG в RGBA; missing texture → fallback
- [x] Переключить с mapping-based API на resource-location-based API
- [x] Загружать только texture IDs, которые реально нужны registry

Acceptance: fake pack works; Faithful folder/zip работает вручную; third-party assets не коммитятся.

---

### T4 — Atlas builder from active pack ✅
- [x] `build_texture_atlas(tiles, *, tile_size) -> GeneratedAtlas` — generic packer
- [x] `create_default_block_tiles()` — default procedural tiles
- [x] Переключить ключи атласа на `minecraft:block/*` resource locations
- [x] Собирать список texture IDs из `BlockRegistry` (из `texture_top/side/bottom` полей)
- [x] Для каждого ID искать в active pack → fallback если не найдено

Acceptance: `None` pack → default atlas; Faithful pack → imported atlas; все IDs из blocks.toml имеют UVs.

---

### T5 — Renderer integration ✅
- [x] `resource_pack_path: str = ""` в `GraphicsSettings`
- [x] `apply_texture_pack()` метод на `DemoWorldRenderer`
- [x] `_meshing_workers` и `_meshing_backend` сохранены на self
- [x] Обновить `load_active_block_atlas()` под новый подход (без mapping TOML)
- [x] При пустом `resource_pack_path` → default atlas с `minecraft:block/*` ключами

Acceptance: `uv run pytest -m smoke`

---

### T6 — Runtime apply in open world ✅ (код реализован, нужна ручная проверка)
- [x] `DemoWorldRenderer.apply_texture_pack(atlas)` — GPU swap + remesh
- [x] Thread/process backend handling
- [x] Old texture release, mesh cache clear, `_remesh_all()`
- [x] Добавить команду `/resourcepack <path|default>` в GameplayController
- [x] При ошибке оставить старый pack
- [ ] Ручная проверка Faithful folder/zip в открытом мире

Ручной тест:
```
1. Запустить игру, создать мир
2. /resourcepack resource_packs/Faithful-32x-1.21.11
3. stone/dirt/grass/oak изменились без рестарта
4. Новые чанки тоже с новым атласом
5. /resourcepack default — визуал откатывается
```

Acceptance: `uv run pytest -m integration`

---

### T7 — UI Texture Pack picker (отдельно, после T1-T6)
- [x] Settings → Texture Packs screen
- [x] Список: Default + ZIP/folders из `resource_packs/`
- [x] Apply выбранного pack; показывать missing/warnings; сохранять выбор

---

### T8 — Cache (опционально, после T7)
- [x] `saves/texture_cache/<pack-id>-<hash>/` — atlas PNG + JSON
- [x] Инвалидация по mtime + размеру пака

---

### Future extension: custom namespaces
Когда появятся свои блоки — не менять архитектуру, просто добавить namespace:
```toml
texture_top = "veilstone:block/my_block_top"
```
Resolver `<namespace>:<kind>/<name>` → `assets/<namespace>/textures/<kind>/<name>.png` уже поддерживает любой namespace. Обычные Minecraft паки покрывают `minecraft:*`, Veilstone-specific паки добавляют `assets/veilstone/textures/block/*.png`.

---

### Риски

| Риск | Митигация |
|------|-----------|
| UV-мисматч при смене — старые меши на старые UV | `mesh_cache.release()` + `_remesh_all()` |
| Утечка GPU-текстуры | `old_texture.release()` до замены |
| Отсутствующая текстура → невидимые блоки | Всегда fallback; атлас содержит все IDs из blocks.toml |
| Animated strip (water) отображается некорректно | MVP: первый кадр |
| UI apply во время мешинга (race) | clear pending queue + remesh после |

---

## Phase 3: Extensibility Architecture

### 3.1 Event Bus
- [ ] `engine/events.py` — EventBus на dataclass events
- [ ] BlockPlaced, BlockBroken, EntityDamaged, EntityDied
- [ ] Подключить audio через event bus
- [ ] Тесты: unit

### 3.2 World Generation Pipeline
- [ ] DimensionDef → [HeightProvider, SurfacePlacer, FeatureDecorator]
- [ ] TerrainGenerator использует pipeline
- [ ] Новый биом = новый decorator
- [ ] Тесты: unit + integration

### 3.3 Game State Machine
- [ ] GameState enum: LOADING, MENU, PLAYING, PAUSED
- [ ] State transitions с валидацией
- [ ] Тесты: unit

---

## Phase 4: Quality & Testing

### 4.1 Missing Unit Tests
- [ ] Unit тесты для WorldManager (Phase 1.4)
- [ ] Unit тесты для GameplayController (Phase 1.5)
- [ ] E2E тесты со скриншотами (verify skill)

### 4.2 Performance
- [ ] Кеширование `_saved_worlds()`
- [ ] Профилирование chunk loading
- [ ] Magic numbers → GameplayConstants

---

## Commit Strategy

Каждая подфаза коммитится отдельно после прохождения тестов.
Никогда не добавлять в сообщения коммитов: `Co-Authored-By: Claude`, `Generated-By`, AI-атрибуцию.
