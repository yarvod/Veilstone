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

### 1.2 InputHandler (~10 методов)
- [ ] Извлечь on_key_press, on_mouse_*, on_text, on_scroll
- [ ] Dispatch events → контроллерам через callbacks
- [ ] Тесты: unit

### 1.3 NetworkController (~12 методов)
- [ ] Извлечь connect_remote, process_network_*, sync_remote_*
- [ ] Извлечь lan_*, open_to_lan, _send_block_action
- [ ] Тесты: unit + integration

### 1.4 WorldManager (~8 методов)
- [ ] Извлечь create_world, load_world, switch_world, save_player
- [ ] Извлечь _saved_worlds (+ кеширование!)
- [ ] Тесты: unit

### 1.5 GameplayController (~8 методов)
- [ ] Извлечь maintain_population, execute_command, difficulty
- [ ] Command registry вместо if/elif chain
- [ ] Тесты: unit

### 1.6 Slim GameWindow
- [ ] GameWindow → координатор (on_draw, fixed_update)
- [ ] ~500 строк вместо 2614
- [ ] Integration тесты

---

## Phase 2: Data-Driven Content

### 2.1 Blocks from TOML/JSON
- [ ] `data/blocks.toml` — определения блоков
- [ ] BlockRegistry загружает из файла
- [ ] Auto-ID assignment
- [ ] Тесты: unit

### 2.2 Biomes from TOML
- [ ] `data/biomes.toml` — параметры биомов
- [ ] BiomeRegistry с настраиваемыми параметрами
- [ ] Тесты: unit

### 2.3 Items from TOML
- [ ] `data/items.toml` — определения предметов
- [ ] ItemRegistry загружает из файла
- [ ] Тесты: unit

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
