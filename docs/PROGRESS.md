# Progress

## Current phase

Phase 13 - Local multiplayer MVP: in progress.

## Completed checklist

### Phases 01-05

- [x] Project/window/shader foundation (`phase-01-complete`, `phase-02-complete`).
- [x] NumPy blocks and chunks (`phase-03-complete`).
- [x] Visible-face rendering, atlas, cache, and culling (`phase-04-complete`).
- [x] Deterministic terrain, features, background streaming (`phase-05-complete`).

### Phase 06 - First-person player and collision

- [x] Player transform, eye position, gravity, walking, and jumping.
- [x] Axis-separated voxel AABB collision with movement substeps.
- [x] Camera mouse look synchronized to the player eye.
- [x] Voxel DDA raycast with hit block, previous placement cell, normal, and distance.
- [x] Gold wireframe block highlight and center crosshair.
- [x] Left-click break and right-click grass placement with player-overlap validation.
- [x] Changed blocks trigger local section remeshing.
- [x] Session-local block deltas survive chunk unload/reload.
- [x] Unit tests for DDA/AABB and integration test against generated terrain.
- [x] Final gate: 52 tests, Ruff, Pyright, client/server smoke, and all benchmarks.
- commits: `76673af`, `3217f56`, `5ca881f`.
- tag: `phase-06-complete`.

### Phase 07 - Lighting MVP

- [x] Direct skylight and per-voxel block-light arrays with chunk relighting.
- [x] Gloam Lantern block emitting warm light at level 14.
- [x] Separate skylight, block light, and ambient occlusion mesh attributes.
- [x] Smooth vertex lighting and AO runtime toggles.
- [x] Day/night terrain tint and sky color cycle.
- [x] Distance fog with a runtime toggle and configurable range.
- [x] Block edits relight and remesh affected loaded chunks.
- [x] Graphics settings in `config/settings.toml`.
- [x] Unit coverage for propagation, vertex lighting, AO, and atmosphere.
- [x] Final gate: 63 tests, Ruff, Pyright, client/server smoke, and lighting/mesher benchmarks.
- commits: `0edffc4`, `0a17218`, `98bacb8`.
- tag: `phase-07-complete`.

### Phase 07 manual-test fixes

- [x] Clear held movement keys when pausing or losing window focus.
- [x] Release and restore exclusive mouse capture across window deactivation.
- [x] Find the nearest spawn column with solid support and clear body/head space.
- [x] Use block `is_solid` metadata for player collision.
- [x] Bind physical macOS `W/A/S/D` positions independently of the active keyboard layout.
- [x] Select voxel AO quad diagonals from vertex brightness to remove cross-shaped shading artifacts.
- commits: `44079e4`, `f159afc`.

### Phase 08 - Greedy meshing

- [x] Halo-aware meshing reads neighboring block, skylight, and block-light data.
- [x] Greedy opaque meshing preserves material, vertex light, and AO signatures.
- [x] Atlas textures repeat per block across merged quads with deterministic variation.
- [x] `F9` switches to the visible-face fallback for visual comparison.
- [x] Debug overlay reports active mesher, quads/faces, and triangle count.
- [x] Skylight spreads laterally below roofs/canopies with bounded NumPy propagation.
- [x] Offscreen framebuffer QA compared greedy and fallback rendering.
- [x] Final gate: 65 tests, Ruff, Pyright, client/server smoke, offscreen OpenGL render, and
  all benchmarks.
- commits: `cb3239f`, `fc165f7`.
- tag: `phase-08-complete`.

### Phase 08 streaming performance fixes

- [x] Replace per-voxel Python halo reads with vectorized section slice copies.
- [x] Run worldgen/lighting and greedy meshing in reusable process pools.
- [x] Upload at most two completed section meshes per frame.
- [x] Add mesh queue telemetry and streaming/frame benchmarks.
- [x] Frame streaming benchmark: approximately `0.73 ms` average, `1.97 ms` p95, and
  `4.72 ms` maximum render integration time while loading 25 chunks.

### Phase 09 - Water

- [x] Water block and generated lakes below world water level.
- [x] Water excluded from opaque meshes and rendered in a back-to-front transparent pass.
- [x] Dedicated animated water shader with subtle surface waves and UV drift.
- [x] Fluid metadata levels control rendered surface height.
- [x] Deterministic downward and horizontal propagation without same-tick cascading.
- [x] Underwater fog switches to a short blue visibility range.
- [x] Water sources persist through session-local chunk unload/reload.
- [x] Safe spawn rejects fluid-filled body and head cells.
- [x] `3` selects a debug water source for placement.
- [x] Final gate: 73 tests, Ruff, Pyright, client/server smoke, and all core benchmarks.
- commit: `18d0397`.
- tag: `phase-09-complete`.

### Phase 10 - Inventory, items, and crafting

- [x] Immutable item definitions, registry, stack limits, block-item mapping, and block drops.
- [x] 9-slot hotbar plus 27-slot backpack with merge, split, swap, and quick-move operations.
- [x] Mouse inventory interactions: left transfer/swap, right split/place-one, Shift-click quick move.
- [x] Session world-drop store with radius pickup, partial pickup, and `Q` drop action.
- [x] Shaped and shapeless recipe engine with trimmed patterns and atomic inventory crafting.
- [x] Player 2x2 crafting and Runecraft Table 3x3 crafting access.
- [x] TOML recipes for Veilwood Planks, Runecraft Table, and Gloam Lantern.
- [x] Placeable Veilwood Planks and Runecraft Table blocks with generated original textures.
- [x] Water Vessel item provides the optional bucket-like water-source placement path.
- [x] Property-based inventory count invariant and drop-to-crafting integration coverage.
- [x] Final gate: 86 tests, Ruff, Pyright, OpenGL inventory/crafting smoke, and benchmarks.
- commit: `f8d4feb`.
- tag: `phase-10-complete`.

### Phase 11 - Entities and mobs

- [x] Integer EntityId allocation and typed dense-dict component stores.
- [x] Transform, Velocity, Collider, Health, RenderModel, MobAI, Lifetime, and ItemEntity.
- [x] Shared cube renderer and shader for visible item, passive, and hostile entities.
- [x] Passive wander and hostile chase/attack state transitions with deterministic steering.
- [x] Water avoidance, distance despawn, and local population replenishment around the player.
- [x] Player health, hostile contact damage, death, and respawn loop.
- [x] View-direction mob targeting, damage, death, and ECS item drops.
- [x] ECS item pickup replaces the temporary invisible drop store in gameplay.
- [x] Unit coverage for storage cleanup, health, AI transitions, spawn rules, death, and pickup.
- [x] Final gate: 92 tests, Ruff, Pyright, entity shader/application smoke, and benchmarks.
- commit: `26f4d17`.
- tag: `phase-11-complete`.

### Phase 12 - Save/load

- [x] Versioned `level.toml` metadata with stable world seed and update timestamp.
- [x] Atomic zlib-compressed binary chunk files with magic, version, and coordinates.
- [x] Blocks, metadata, skylight, and block light round-trip for every chunk section.
- [x] Player position, health, selected hotbar slot, and full inventory persistence.
- [x] Dirty SAVE flag integration at autosave, chunk unload, and application close.
- [x] Process worldgen loads saved chunks before deterministic generation fallback.
- [x] Five-second autosave plus atomic temporary-file replacement.
- [x] Explicit migration dispatch stub rejects unsupported versions.
- [x] Smoke and benchmark runs use temporary worlds instead of modifying player saves.
- [x] Final gate: 96 tests, Ruff, Pyright, persistence restart test, smoke, and benchmarks.
- commit: `fc18e1e`.
- tag: `phase-12-complete`.

### Phase 13 - Local multiplayer MVP (in progress)

- [x] 4 MiB-bounded length-prefixed frames with msgpack maps and binary payloads.
- [x] Threaded TCP server and client with protocol-version handshake and join.
- [x] Player input/state updates and broadcast entity snapshots.
- [x] Chunk request/response with binary voxel payload.
- [x] Block delta and chat broadcast replication.
- [x] Two-client integration test covers join, visibility, input, chunk, block, and chat.
- [x] Dedicated server command now starts the real TCP transport.
- [x] Network benchmark serializes/transfers/decodes 1000 frames at about `0.002 ms/frame`.
- [ ] Connect remote chunk payloads to the graphical client's world/renderer.
- [ ] Wire `client --connect` and in-game Direct Connect UI to `LanClient`.

## Failed checks

None recorded.

## Performance notes

- Player physics benchmark, 20,000 ticks: approximately 3.9 microseconds per tick.
- Full featured terrain generation with lakes remains approximately 10.16 ms per chunk off-thread.
- Lit visible-face meshing with smooth light and AO is approximately 1.33 ms per section.
- Greedy meshing is approximately 2.49 ms and reduces the flat benchmark from 2048 to 12
  triangles.
- Full `16x64x16` chunk relighting with four sources is approximately 1.50 ms.
- Vectorized `18^3` section halo snapshot is approximately 0.02 ms.
- Streaming with opaque and water meshes remains approximately `0.84 ms` average,
  `1.64 ms` p95, and `9.93 ms` maximum after process-pool warmup.
- Process pools warm before gameplay; streaming with persistence enabled measures approximately
  `1.27 ms` average, `2.49 ms` p95, and `3.07 ms` maximum.

## Known bugs

- Block edits persist only for the running session; disk persistence belongs to Phase 12.
- Emissive block-light propagation does not yet transfer energy across chunk boundaries;
  mesh halo sampling itself does cross loaded section/chunk boundaries.
- Fluid propagation is currently chunk-local; cross-chunk flow belongs to later world simulation work.
- Water Vessel can place a source but does not yet scoop an existing source back up.
- Mob navigation is intentionally local steering over terrain height, not global pathfinding.
- Entity models are colored prototype cuboids pending later art/model polish.
- Create World and Load World currently target the same `saves/dev_world`; world selection UI is
  still a later menu polish task.

## Next recommended tasks

Continue Phase 13 by feeding remote chunks and snapshots into the graphical client.
