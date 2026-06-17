# Project Knowledge — Veilstone (voxel_sandbox)

## Architecture Overview

Python voxel sandbox (Minecraft-like) built with Pyglet + ModernGL + NumPy.

### Layer Structure (dependency flows DOWN)
```
app/          — bootstrap, settings, commands, paths
render/       — window (GOD CLASS), world_scene, meshes, UI, entities, shaders
engine/       — chunks, generation, ECS, physics, lighting, water
domain/       — blocks, items, inventory, crafting (pure, no deps)
infrastructure/ — storage, logging
network/      — server, client, discovery, protocol
audio/        — bus, director, backend
```

### Key Files
- `render/window.py` (2614 lines) — GOD CLASS, needs Phase 1 refactor
- `render/world_scene.py` (724 lines) — world rendering + streaming
- `engine/ecs/simulation.py` (432 lines) — entity simulation + mob AI
- `engine/generation/terrain.py` (339 lines) — terrain generation
- `engine/generation/streaming.py` (343 lines) — async chunk loading
- `engine/physics/player.py` — player movement controller
- `engine/physics/raycast.py` — block raycast

### Chunk System
- 16x16 columns, CHUNK_HEIGHT=128, SECTION_SIZE=16
- ChunkCoord(x, z) identifies chunks
- Each Chunk has sections (ChunkSection) with 16x16x16 blocks
- Blocks stored as uint16 IDs in numpy arrays
- Light: sky_light + block_light per voxel (uint8)

### Block Registry
- Hardcoded in `domain/blocks/registry.py:create_core_block_registry()`
- BlockDef: id, key, name, Material, textures, properties
- Block ID 0 = air (required)
- Currently 13 block types

### ECS
- EntityWorld with component storage (Transform, Velocity, Health, MobAI, etc.)
- EntitySimulation handles spawning, AI, physics, damage
- MobKind: PASSIVE, HOSTILE
- Only 2 mob types currently

### Water System
- Block ID for water defined in registry (is_fluid=True)
- simulate_water_step in engine/world/water.py — basic downward fill
- NO horizontal flow, NO source/flowing distinction, NO decay levels

### Rendering
- Pyglet window + ModernGL context
- Greedy meshing for chunks (visible_faces.py → greedy.py)
- MeshingNeighborhood with HALO_RADIUS=2 for boundary faces
- Shaders: chunk_opaque, water, entity, sky, shadow_depth, debug, highlight

### Tests
- pytest in tests/unit/ and tests/integration/
- Run: `.venv/bin/python -m pytest tests/ -x -q`
- Pre-existing failure: test_block_registry (expects 11 blocks, has 13)

### Known Pitfalls
- `_saved_worlds()` reads filesystem every frame (performance)
- `execute_command` is 80-line if/elif chain
- Magic numbers scattered in window.py
- No event bus — everything through direct method calls
- No proper game state machine
