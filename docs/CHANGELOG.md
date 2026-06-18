# Changelog

## [Unreleased]

### Changed
- **InventoryController extracted from GameWindow** — all inventory sprites, hotbar, health bar, held-item hand, and crafting UI moved to `render/inventory_ui.py:InventoryController`; GameWindow delegates via `self._inv_ctrl`

### Added
- **Player swimming** — buoyancy, swim_speed, in_water state in PlayerController
- **Water flow physics** — drain logic removes flowing water without source
- **Mob spawn validation** — 2-block clearance check prevents spawning inside blocks
- **AI obstacle avoidance** — mobs try 45°/90° turns before reversing direction
- **Zombie attack height check** — melee requires abs(dy) <= 2.0 blocks
- **Attack animation reset** — animation phase resets on each hit for visual feedback
- **Mob water physics** — smooth buoyancy with lerp, no more jittering
- **15 water physics tests** — swimming, raycast through water, fluid simulation
- **8 mob/combat tests** — spawn validation, height check, avoidance, animation

### Fixed
- **Font crash on Windows** — replaced hardcoded "Minecraft" font with platform font (Segoe UI / Menlo)
- **World selection buttons broken** — "Create New World" and "Cancel" passed strings instead of MenuCommand enum
- **Enter key doesn't load world** — on Singleplayer screen, Enter now loads selected world
- **World list keyboard navigation** — Up/Down arrows were trapped in text_input block
- **Chunk lighting seams** — neighbor chunks now remeshed when new chunk loads
- **WorldCard selection not visible** — added background + text color change for selected state
- **Label.color not propagating** — added property setter to update underlying pyglet label
- **Draw order flicker** — world list now updates before draw() call
- **Can't break blocks through water** — raycast now skips fluid blocks
- **Player can't swim** — collision uses is_solid callback, water is passable
- **Mobs spawn inside blocks** — spawn checks clearance with is_solid
- **Mobs stuck in water** — smooth buoyancy replaces jerky impulse
- **Zombie attacks through height** — Y-distance check prevents impossible hits
- **SpawnStructureCommand.template_name** — renamed to .key (matched usage)

---

## Format

### Added — new features
### Changed — changes in existing functionality
### Fixed — bug fixes
### Removed — removed features
### Security — vulnerability fixes
