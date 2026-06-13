# Progress

## Current phase

Phase 09 - Water: complete and ready for manual testing.

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

## Failed checks

None recorded.

## Performance notes

- Player physics benchmark, 20,000 ticks: approximately 3.9 microseconds per tick.
- Full featured terrain generation with lakes remains approximately 9.86 ms per chunk off-thread.
- Lit visible-face meshing with smooth light and AO is approximately 1.39 ms per section.
- Greedy meshing is approximately 2.46 ms and reduces the flat benchmark from 2048 to 12
  triangles.
- Full `16x64x16` chunk relighting with four sources is approximately 1.54 ms.
- Vectorized `18^3` section halo snapshot is approximately 0.02 ms.
- Streaming with opaque and water meshes remains approximately `0.84 ms` average,
  `1.64 ms` p95, and `9.93 ms` maximum after process-pool warmup.

## Known bugs

- Block edits persist only for the running session; disk persistence belongs to Phase 12.
- Emissive block-light propagation does not yet transfer energy across chunk boundaries;
  mesh halo sampling itself does cross loaded section/chunk boundaries.
- Fluid propagation is currently chunk-local; cross-chunk flow belongs to later world simulation work.
- Water has a debug placement key; bucket behavior belongs to the Phase 10 item system.

## Next recommended tasks

Test Phase 09 water, then continue with Phase 10 inventory, items, and crafting.
