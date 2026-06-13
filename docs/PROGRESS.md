# Progress

## Current phase

Phase 05 - Terrain generation: complete and ready for manual testing.

## Completed checklist

### Phase 01 - Project skeleton

- [x] Python 3.13 `uv` project, Ruff, pytest, Pyright, logging, config, and CLI.
- [x] Player-facing no-argument entry point and developer server/client commands.
- [x] Pyglet window, ModernGL context, camera input, FPS/frame-time overlay.
- commits: `3e51c4b`, `5e0ee3c`, `e4dc47e`; tag: `phase-01-complete`.

### Phase 02 - OpenGL client shell

- [x] GLSL loading, compilation, timestamp hot reload, and manual `F5` reload.
- commit: `39abdea`; tag: `phase-02-complete`.

### Phase 03 - Blocks and chunks

- [x] Immutable block definitions and validated registry.
- [x] Chunk/section coordinates, negative coordinate conversion, NumPy storage.
- [x] Dirty flags, revisions, World protocol, and in-memory world access.
- commits: `a846ccb`, `b93c292`; tag: `phase-03-complete`.

### Phase 04 - Basic meshing and rendering

- [x] Vectorized visible-face meshing with indexed position/UV/normal buffers.
- [x] Original generated texture atlas, ModernGL VBO/IBO upload, chunk shader.
- [x] Section mesh cache, frustum culling, and mesh debug statistics.
- commits: `6c9da62`, `757a957`, `7ff01f2`, `c52faa9`; tag: `phase-04-complete`.

### Phase 05 - Terrain generation

- [x] Stable numeric/text seeds, smooth heightmap, and four MVP biomes.
- [x] Stone/dirt/grass layers, veilwood trees, dusk crystal ore, and caves.
- [x] Camera-centered chunk requests and deterministic generation tests.
- [x] Background worldgen workers, completed upload queue, and chunk unloading.
- [x] Streamed section rendering and loaded/pending/visible debug statistics.
- [x] Final gate: 43 tests, Ruff, Pyright, client/server smoke tests, and both benchmarks.
- commits: `a5ede0a`, `dc6b92f`, `211346b`, `5bb4332`.
- tag: `phase-05-complete`.

### UI foundation pulled forward from Phase 17

- [x] Main Menu, Singleplayer/Multiplayer shells, Pause Menu, and Open to LAN placeholder.
- [x] One player-facing entry point; no separate player-facing `host` command.
- commits: `27fa351`, `8a46ce0`.

## Failed checks

None recorded.

## Performance notes

- Visible-face meshing, half-solid `16^3`: approximately 0.24 ms average.
- Full terrain generation with features: approximately 8.3 ms per chunk.
- World generation runs outside the render thread; GPU uploads are capped per frame.
- Voxel storage uses `uint16` block IDs and `uint8` auxiliary NumPy arrays.

## Known bugs

- Section meshing currently treats neighboring sections/chunks as air, producing hidden duplicate
  boundary faces. Cross-section world views will remove these during later meshing work.
- Create/Load World currently enters the configured development seed; save selection belongs to Phase 12.

## Next recommended tasks

Stop after Phase 05 for manual testing. Begin Phase 06 only after the milestone is accepted.
