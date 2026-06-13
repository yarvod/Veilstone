# Progress

## Current phase

Phase 06 - First-person player and collision: complete and ready for manual testing.

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

## Failed checks

None recorded.

## Performance notes

- Player physics benchmark, 20,000 ticks: approximately 3.7 microseconds per tick.
- Visible-face meshing remains approximately 0.24 ms for the benchmark section.
- Full featured terrain generation remains approximately 8.3 ms per chunk off-thread.

## Known bugs

- Block edits persist only for the running session; disk persistence belongs to Phase 12.
- Section meshing still treats neighboring sections/chunks as air, leaving hidden boundary faces.
- Placing currently uses a fixed grass block because inventory/hotbar arrives in Phase 10.

## Next recommended tasks

Stop after Phase 06 for manual testing. Begin Phase 07 only after acceptance.
