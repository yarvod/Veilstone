# Veilstone — Plan Work / Рабочий план

## Overview

Рефакторинг архитектуры + исправление критических багов движка.
Цель: сделать проект расширяемым для добавления новых фич (блоки, биомы, мобы, измерения).

---

## Phase 0: Critical Engine Bugs (PRIORITY)

Баги, которые ломают геймплей прямо сейчас.

### 0.1 Water Physics — Плавание и течение ✅
- [x] **Игрок не может плавать** — добавлен buoyancy, swim_speed, in_water
- [x] **Вода не течёт** — добавлен drain, horizontal spread with decay
- [x] **Нельзя ломать блоки сквозь воду** — raycast skip_block для fluids

### 0.2 Mob AI & Physics ✅
- [x] **Мобы застревают в воде** — smooth buoyancy с lerp
- [x] **Мобы спавнятся внутри блоков** — проверка 2-block clearance
- [x] **AI не обходит препятствия** — попытка 45°/90° поворота перед разворотом
- [x] **Зомби бьёт игрока сквозь высоту** — проверка abs(dy) <= 2.0

### 0.3 Combat & Animation ✅
- [x] **Анимация удара зомби** — state_phase сбрасывается при каждом ударе
- [x] **Высотная проверка атаки** — зомби не бьёт если игрок >2 блока выше

---

## Phase 1: Extract GameWindow God Class

Разбить `window.py` (2614 строк, 92 метода) на контроллеры.

### 1.1 InventoryController (~15 методов)
- [ ] Извлечь draw_hotbar, draw_health, draw_inventory
- [ ] Извлечь crafting_*, inventory_slot_*, handle_crafting_click
- [ ] Все pyglet спрайты инвентаря → в контроллер
- [ ] Тесты: unit + integration

### 1.2 InputHandler (~10 методов) ✅
- [x] Извлечь on_key_press, on_mouse_*, on_text, on_scroll
- [x] Dispatch events → контроллерам через callbacks
- [x] Тесты: unit (42 теста)

### 1.3 NetworkController (~12 методов) ✅
- [x] Извлечь connect_remote, process_network_*, sync_remote_*
- [x] Извлечь lan_*, open_to_lan, _send_block_action
- [x] Тесты: unit (33 теста)

### 1.4 WorldManager (~8 методов) ✅
- [x] Извлечь create_world, load_world, switch_world, save_player
- [x] Извлечь _saved_worlds, _world_slug → render/world_manager.py
- [ ] Тесты: unit

### 1.5 GameplayController (~8 методов) ✅
- [x] Извлечь maintain_population, execute_command, _set_difficulty
- [x] Извлечь _hostile_spawn_allowed, _is_entity_hazard → render/gameplay_controller.py
- [x] match/case dispatch вместо 80-строчного if/elif chain
- [ ] Тесты: unit

### 1.6 Slim GameWindow ✅ (partial)
- [x] Extract MenuUI (menu rendering, text input, world list, audio helpers) → render/menu_ui.py
- [x] GameWindow delegates _draw_menu/_prepare_ui_draw/_draw_text_input to menu_ui
- [ ] GameWindow → чистый координатор (on_draw, fixed_update)
- [ ] ~500 строк вместо 1488
- [ ] Integration тесты

---

## Phase 2: Data-Driven Content

### 2.1 Blocks from TOML ✅
- [x] `data/blocks.toml` — определения блоков
- [x] `load_block_registry_from_toml()` — загрузка из файла
- [x] Auto-ID assignment (если id не указан)
- [x] window.py, world_scene.py, server.py загружают из TOML
- [x] Тесты: unit (3 теста)

### 2.2 Biomes from TOML ✅
- [x] `data/biomes.toml` — параметры биомов
- [x] `BiomeDef` + `BiomeRegistry` в domain/biomes/
- [x] `load_biome_registry_from_toml()` — загрузка из файла
- [x] Тесты: unit (7 тестов)

### 2.3 Items from TOML ✅
- [x] `data/items.toml` — определения предметов + drop table
- [x] `load_item_registry_from_toml()` — загрузка из файла
- [x] window.py загружает из TOML
- [x] Тесты: unit (2 теста)

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

### 4.1 Test Coverage
- [ ] Unit тесты для каждого извлечённого контроллера
- [ ] Integration тесты для game flow
- [ ] E2E тесты со скриншотами (verify skill)

### 4.2 Performance
- [ ] Кеширование _saved_worlds()
- [ ] Профилирование chunk loading
- [ ] Magic numbers → GameplayConstants

---

## Commit Strategy

Каждая подфаза коммитится отдельно после прохождения тестов:
- `Phase 0.1: Fix water physics — swimming, flow, block breaking through water`
- `Phase 0.2: Fix mob spawning, AI pathfinding, water navigation`
- `Phase 0.3: Fix zombie attack height check, add hit animation`
- `Phase 1.1: Extract InventoryController from GameWindow`
- и т.д.
