# Changelog

## [Unreleased]

### Added
- **World generation pipeline** — `HeightProvider`, `SurfacePlacer`, `FeatureDecorator` protocols + `DimensionDef` in `engine/generation/pipeline.py`; `BiomeSurfacePlacer` reads block IDs from `BlockRegistry`+`BiomeRegistry` so biome surface blocks come from `data/biomes.toml` (highlands = stone, swamp = dirt, etc.); wired in world_scene.py.
- **GameState machine** — `GameState` enum (MENU / PLAYING / PAUSED) + `GameStateMachine` with validated transitions in `engine/game_state.py`; `GameWindow.game_state` field synced at all screen transitions via `_sync_game_state()`.
- **Gameplay constants** — named constants extracted to `engine/gameplay_constants.py` (player position bounds, world limits, terrain heights, tree/ore density thresholds) replacing scattered magic numbers.
- **`_saved_worlds()` cache** — `WorldManager._saved_worlds()` caches filesystem scan at class level; invalidated on `create_world()`.
- **Minecraft Java resource pack MVP** — block texture IDs now use `minecraft:block/*` resource locations; folder/ZIP packs can be imported for block atlases, and `/resourcepack <path|default>` hot-swaps the active atlas in an open world.
- **Texture pack picker** — Settings now includes a Texture Packs screen with Default plus discovered folder/ZIP packs from `resource_packs/`, apply/default actions, and import fallback/missing status.
- **Texture atlas cache** — imported resource pack atlases are cached as PNG+JSON under `texture_cache` and invalidated when pack file size/mtime changes.
- **Gameplay EventBus** — block and entity gameplay events now flow through `engine/events.py`, with audio subscribed as an event listener.

### Changed
- **HudController extracted from GameWindow** — all HUD labels (debug, position, player list, crosshair, nametags), debug text building, and `on_draw` HUD block moved to `render/hud_controller.py`; GameWindow delegates via `self._hud`
- **Player position helpers moved to WorldManager** — `restore_player_position`, `invalid_player_position_reason`, `move_player_to_spawn` are now on `WorldManager`; `GameWindow.__init__` creates `_worlds` early to enable this
- **`apply_rebind` moved to InputHandler** — control rebinding logic extracted from GameWindow; InputHandler now owns the full rebind flow
- **`toggle_structure` moved to NetworkController** — structure toggle network/LAN dispatch no longer lives in GameWindow
- **Dead profiling state removed** — unused `_prof_*` instance variables and local `_prof_start`/`_prof_frame_start_time` dropped
- **window.py: 863 → 579 lines** — Phase 1.6 complete; GameWindow is now a thin coordinator
- **InventoryController extracted from GameWindow** — all inventory sprites, hotbar, health bar, held-item hand, and crafting UI moved to `render/inventory_ui.py:InventoryController`; GameWindow delegates via `self._inv_ctrl`
- **MenuUI owns its widgets** — text input overlays, panels, labels, world list state moved from `GameWindow.__init__` into `MenuUI.__init__`; dead code (`menu_labels`, `world_list_labels`, `world_list_last_click`) deleted
- **Fix `_begin_text_input` call path** — `input_state.py` now calls `win.menu_ui._begin_text_input()` instead of the missing `win._begin_text_input()` (was an AttributeError at runtime)
- **Thin wrapper removal from GameWindow** — ~25 delegate stubs deleted (`execute_command`, `open_to_lan`, `create_world`, `load_world`, `_connect_remote`, `_stop_network_services`, `_maintain_population`, etc.); callers in `input_state.py`, `menu_ui.py`, `world_manager.py`, and tests updated to use controllers directly (`win._gameplay.*`, `win._net.*`, `win._worlds.*`)

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
- **Saved world loading after MenuUI extraction** — refreshed world lists now use `WorldManager`, fixing `GameWindow._saved_worlds` AttributeError.
- **Menu hover sound spam** — UI hover audio now plays only on button hover entry instead of every handled mouse-motion event.
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
