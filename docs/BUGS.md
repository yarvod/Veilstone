# Known Bugs & Issues

## Critical — Gameplay Breaking

### BUG-001: Player cannot swim in water
- **Status:** Open
- **Description:** Нет buoyancy в PlayerController. Игрок тонет и не может подняться.
- **Root cause:** PlayerController не проверяет is_fluid для текущего блока
- **Files:** `engine/physics/player.py`

### BUG-002: Cannot break blocks through water
- **Status:** Open
- **Description:** Raycast останавливается на воде, не позволяя ломать блоки за ней
- **Root cause:** Raycast считает воду solid для hit detection
- **Files:** `engine/physics/raycast.py`, `render/world_scene.py`

### BUG-003: Water has no flow physics
- **Status:** Open
- **Description:** Вода статична — нет source/flowing/decay механики как в Minecraft
- **Root cause:** simulate_water_step только заполняет вниз, нет горизонтального spread с decay
- **Files:** `engine/world/water.py`, `render/world_scene.py`

## High — Major Issues

### BUG-004: Mobs get stuck in water and jitter
- **Status:** Open
- **Description:** Мобы входят в воду и дёргаются, не могут выбраться
- **Root cause:** AI не имеет water navigation, физика мобов не учитывает buoyancy
- **Files:** `engine/ecs/simulation.py`

### BUG-005: Mobs spawn inside solid blocks
- **Status:** Open
- **Description:** Мобы появляются внутри земли/камня и застревают
- **Root cause:** spawn position validation не проверяет 2-высотный clearance
- **Files:** `render/window.py:_maintain_population`, `engine/ecs/simulation.py`

### BUG-006: Zombie attacks through height
- **Status:** Open
- **Description:** Зомби может ударить игрока находящегося высоко над ним
- **Root cause:** Нет Y-distance проверки в damage calculation
- **Files:** `engine/ecs/simulation.py`

### BUG-007: Zombie attack has no animation
- **Status:** Open
- **Description:** При ударе зомби нет анимации атаки
- **Root cause:** Нет attack animation state в MobState/AnimationState
- **Files:** `engine/ecs/simulation.py`, `render/entity_animation.py`

### BUG-008: Mob AI cannot navigate around obstacles
- **Status:** Open
- **Description:** Мобы упираются в стену и стоят, не пытаясь обойти
- **Root cause:** AI использует прямое направление к цели без pathfinding
- **Files:** `engine/ecs/simulation.py`

## Resolved

### BUG-R001: Font crash on Windows ✅
- **Fixed in:** commit 501e26e

### BUG-R002: World selection buttons broken ✅
- **Fixed in:** commit 501e26e

### BUG-R003: Chunk lighting seams ✅
- **Fixed in:** commit 501e26e
