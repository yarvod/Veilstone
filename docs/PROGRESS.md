# Progress

## Current phase

Phase 20 - Articulated mobs and procedural animation: complete. Phase 21 moving structures is next.

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
- [x] Treat unloaded chunks and the lower world boundary as collision barriers.
- [x] Preload collision chunks before restoring a saved position.
- [x] Recover invalid/out-of-world saved positions at safe spawn without losing player state.
- [x] Add unit and OpenGL smoke regressions for saved-position recovery.
- commits: `44079e4`, `f159afc`, `79249a1`.

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

### Phase 13 - Local multiplayer MVP

- [x] 4 MiB-bounded length-prefixed frames with msgpack maps and binary payloads.
- [x] Threaded TCP server and client with protocol-version handshake and join.
- [x] Player input/state updates and broadcast entity snapshots.
- [x] Chunk request/response with binary voxel payload.
- [x] Block delta and chat broadcast replication.
- [x] Two-client integration test covers join, visibility, input, chunk, block, and chat.
- [x] Dedicated server command now starts the real TCP transport.
- [x] Network benchmark serializes/transfers/decodes 1000 frames at about `0.002 ms/frame`.
- [x] Compressed server chunks decode into client `Chunk` objects and render through the existing
  lighting, meshing, cache, and GPU pipeline.
- [x] `client --connect HOST:PORT` starts a remote graphical session on a temporary local cache.
- [x] Remote player snapshots render through ECS as distinct player proxies.
- [x] Graphical remote-client smoke verifies a server chunk is installed and a frame renders.
- [x] Final gate: 100 tests, Ruff, Pyright, client/server/remote-render smoke, and benchmarks.
- commits: `456053d`, `d1b58ff`.
- tag: `phase-13-complete`.

### Phase 14 - Multiplayer polish

- [x] Delayed snapshot interpolation smooths remote-player transforms.
- [x] Local prediction remains immediate and bounded reconciliation corrects authoritative error.
- [x] Remote mode disables local terrain generation to prevent mixed client/server worlds.
- [x] Client requests nearby server chunks incrementally by distance and request budget.
- [x] Server rejects chunk requests outside the configured interest radius.
- [x] Entity snapshots are filtered per client to a 64-block visibility radius.
- [x] Per-client token buckets limit input/action/chat/request traffic.
- [x] UDP LAN discovery advertises world name, game port, and current player count.
- [x] Sequence-numbered entity deltas use periodic full baselines and explicit removals.
- [x] Client session supports bounded reconnect attempts to its previous target.
- [x] `--name` selects a bounded LAN nickname and `Join LAN World` uses discovery results.
- [x] Shared text input supports Direct Connect, nickname editing, and multiplayer chat.
- [x] Exhausted reconnect attempts return the player to Multiplayer with a visible status.
- [x] Singleplayer starts and connects to an in-process authoritative server.
- [x] Open to LAN advertises that existing server and shares the active persisted world.
- [x] Dedicated server reads and persists the configured `--world` save.
- [x] Remote block actions are range-validated and applied to the host world on the render thread.
- [x] Integration coverage verifies discovery, join position, rename, reconnect, active-world edits,
  and server persistence.
- [x] Server benchmark covers 8 players, 200 mobs, interest filtering, and snapshot encoding.
- [x] Final gate: 114 tests passed; 4 display-dependent OpenGL smoke tests skipped in the final
  headless shell after passing targeted runs earlier; Ruff, Pyright, server smoke, and benchmarks pass.
- commits: `92e833d`, `995afd8`, `e2fb4b9`, `5932913`, `5f06b17`, `219338c`, `d2b4b2e`.

### Phase 15 - Shadows and shader polish

- [x] Configurable `off`, `low` (1024), and `medium` (2048) shadow-map quality.
- [x] Stable texel-snapped directional sun view-projection matrix.
- [x] Depth texture/framebuffer and depth-only opaque chunk pass.
- [x] Additional depth VAOs are built at mesh upload time, not during frame rendering.
- [x] Opaque chunk shader samples the shadow map with configurable bias and 3x3 PCF.
- [x] Entity geometry uses a matching animated depth-only shadow pass.
- [x] Sun shadowing leaves emissive block-light contribution unshadowed.
- [x] Unit coverage for quality mapping and stable finite sun matrices.
- [x] `benchmark-shadows` forces GPU completion and enforces a 12 ms medium-shadow p95 budget.
- [x] Water uses two animated wave layers, sky Fresnel tint, and surface/side transparency.
- [x] One-pass procedural sky renders day/night gradients, synchronized sun/moon, and clouds.
- [x] Optional resize-safe postprocess provides tone mapping and vignette after world rendering.
- [x] GPU smoke covers medium, low, off, postprocess resize, and framebuffer restoration.
- [x] Guaranteed respawn expands across prepared chunks and creates an emergency safe column.
- [x] Final gate: 124 tests, Ruff, Pyright, client/server smoke, and all Phase 15 benchmarks pass.
- [x] Medium shadow p95 is `0.31 ms` against the `12 ms` budget; full streaming p95 is `2.74 ms`.
- commits: `4742e88`, `0111f90`, `af67cb1`, `bfc2516`, `4be9097`, `3a13d95`.

### Phase 16 - Structures and world richness

- [x] Versioned TOML templates validate dimensions, coordinates, block IDs, rarity, and loot.
- [x] Seeded region placement is deterministic and independent of chunk generation order.
- [x] Terrain suitability rejects water footprints and slopes above three blocks.
- [x] Cross-chunk placement applies the same anchor and template to every intersecting chunk.
- [x] Original veilstone ruin, veilwood camp, and rare dusk spire templates.
- [x] Deterministic weighted loot-roll API for future structure containers.
- [x] Existing caves and dusk crystal resources remain integrated before structures.
- [x] `structure-preview TEMPLATE` prints validated templates by layer with loot metadata.
- [x] Golden tests cover all structure types, actual generated blocks, loot, and determinism.
- [x] Final gate: 129 tests, Ruff, Pyright, client smoke, and wheel data verification pass.
- [x] Worldgen remains approximately `9.90 ms/chunk` over 100 chunks.
- commit: `00a0dbf`.

### Phase 17 - UI polish and settings

- [x] Create World captures a name and seed and creates an isolated save directory.
- [x] Load World discovers metadata and restores the selected world's player snapshot.
- [x] World switching releases old network, process-pool, mesh, and GPU resources.
- [x] Settings screen exposes shadow quality, clouds, postprocess, and VSync.
- [x] Controls screen supports conflict-checked movement/jump rebinding.
- [x] User settings persist atomically in `saves/settings.toml` and overlay project defaults.
- [x] Existing inventory, crafting, pause, LAN, and debug UI remain accessible from one entry point.
- [x] Integration test verifies Alpha/Beta world seed and player-state isolation.
- [x] Final gate: 134 tests, Ruff, Pyright, and client/server smoke pass.
- commits: `c8287f0`, `29f0b67`, `08fe233`.

### Phase 18 - Packaging

- [x] Original Veilstone PNG, macOS ICNS, and Windows ICO application icons.
- [x] Application version `0.1.0` is reported by `voxel --version`.
- [x] Cross-platform PyInstaller build script includes config, assets, shaders, and templates.
- [x] Frozen multiprocessing initialization supports worldgen and meshing process pools.
- [x] Packaged resources resolve independently of the repository working directory.
- [x] Platform user-data roots hold settings, saves, and append-only crash logs.
- [x] First packaged launch creates an editable user settings file.
- [x] macOS arm64 bundle builds and completes the real OpenGL client smoke test.
- [x] Built wheel installs and completes the same smoke test from a clean environment.
- [x] GitHub Actions matrix defines native macOS, Windows, and optional Linux package smoke jobs.
- [x] Final local gate: 141 tests, Ruff, Pyright, wheel smoke, and macOS bundle smoke pass.
- [x] Native Windows, macOS, and Linux package jobs pass in Actions run `27496080787`.
- [x] Windows verifies executable startup, resources, user-data writes, and dedicated server.
- [x] Linux and macOS complete the packaged OpenGL client smoke test.
- [x] Cross-platform CI exposed and fixed a receiver-thread socket shutdown race.
- commits: `1ba392e`, `d364c7c`, `c5fd635`, `7641db2`.

### Phase 19 - Audio foundation

- [x] Backend protocol with Pyglet and deterministic Null implementations.
- [x] Event bus, TOML registry, master/effects/music/ambience volume groups.
- [x] Positional material block sounds and grounded movement footsteps.
- [x] UI click and mob hit/death hooks.
- [x] Surface/cave ambience and menu/exploration/night music state machine.
- [x] Audio settings screen persists and applies all four volume groups.
- [x] Dedicated server composes the Null backend and imports no playback driver.
- [x] Original procedural WAV set and reproducible asset generator.
- [x] Wheel and PyInstaller resource verification covers registry and audio assets.
- [x] Final gate: 145 tests, Ruff, Pyright, source/frozen client smoke, and server smoke pass.
- commit: `2936e77`.

### Phase 20 - Articulated mobs and procedural animation

- [x] Versioned TOML skeleton/model and animation clip formats.
- [x] Shared texture atlas with per-part material, UV, tint, transform, and hierarchy data.
- [x] Original image-generated Veilgrazer and Gloamstalker pixel skins.
- [x] Distinct quadruped passive and upright hostile silhouettes with nine parts each.
- [x] AnimationGraph, PoseBlender, local state phases, and reusable procedural controllers.
- [x] Independent head, limb, tail, jaw, ear, and horn transforms.
- [x] Idle bob, speed-synchronized gait, attack, hurt, and delayed death poses.
- [x] LAN player animation state/phase replication and articulated remote player model.
- [x] Distance culling plus body/head LOD beyond 28 blocks.
- [x] Rendered OpenGL smoke verifies at least 18 part draws for two mobs.
- [x] Animation state summary in the debug overlay.
- [x] Final gate: 154 tests, Ruff, Pyright, wheel/frozen resource checks, and client smoke pass.
- [x] Articulated shadow benchmark remains `0.35 ms` p95 against the `12 ms` budget.

### Phase 20.1 - Difficulty and command line post-pass

- [x] Persisted Settings option cycles between peaceful and normal difficulty.
- [x] Peaceful mode immediately removes hostile mobs and prevents replenishment.
- [x] Normal mode caps nearby hostile population at one and replenishes every five seconds.
- [x] Hostile candidates require a loaded chunk and effective skylight/block light at level 7 or less.
- [x] `/` opens the command line with `/help`, `/time set ...`, and `/difficulty ...` commands.
- [x] Unit tests cover parsing, persistence, lighting and population rules.
- [x] Hidden-window integration verifies time changes and peaceful hostile removal.
- [x] Final gate: 164 tests, Ruff and Pyright pass.
- commit: `11b3ce0`.

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
- Multiplayer server tick with 8 players and 200 mobs measures approximately `0.98 ms` p95
  against the `50 ms` 20 TPS budget.
- Medium shadows measure approximately `0.31 ms` p95; the full streaming render path measures
  approximately `2.74 ms` p95 with a `10.23 ms` observed maximum.

## Known bugs

- Emissive block-light propagation does not yet transfer energy across chunk boundaries;
  mesh halo sampling itself does cross loaded section/chunk boundaries.
- Fluid propagation is currently chunk-local; cross-chunk flow belongs to later world simulation work.
- Water Vessel can place a source but does not yet scoop an existing source back up.
- Mob navigation is intentionally local steering over terrain height, not global pathfinding.

## Next recommended tasks

Begin Phase 21 with BlockEntity storage and transform-driven moving structures.
