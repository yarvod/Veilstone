# Veilstone Backlog

This backlog captures observed product gaps that should feed future active
`docs/WORKPLAN.md` phases. Keep `WORKPLAN` focused on work currently being
implemented; move backlog items into `WORKPLAN` only when the slice becomes
active.

Items in this file may include implementation sketches. Treat those sketches as
directional notes, not accepted design until promoted into an active plan and
validated against `docs/ARCHITECTURE.md`.

## Architecture Cleanup

### ARCH-B001: Finish GameWindow Decomposition

- **Status:** open
- **Observed:** `GameWindow` remains the practical composition root and several
  compatibility adapters still expose broad window-like surfaces, despite the
  existing HUD/debug/player snapshots and controller adapters.
- **Desired:** `GameWindow` becomes a thin presentation shell: application
  use-cases own orchestration, snapshots cross render/network/UI boundaries,
  renderer adapters consume render data, and tests cover most behavior without
  constructing Pyglet/ModernGL objects.
- **Candidate work:** narrow the remaining adapter protocols, extract gameplay
  command use-cases, move world-runtime lifecycle ownership out of the window,
  and add renderer settings ports in independently verified slices.
- **Acceptance idea:** architecture docs/watchlist no longer list `GameWindow`
  as broad runtime owner, import-linter contracts remain green, and new
  Minecraft-feel features can be added without adding state to `render/window.py`.

## Multiplayer

### MP-B001: Second Player Can Spawn Underground Far From Expected Origin

- **Status:** open
- **Observed:** in multiplayer, joining/second player can load underground far
  away from the intended spawn/origin area.
- **Desired:** joining players spawn at a safe, deterministic,
  server-authoritative location near world spawn unless a valid saved player
  position exists.
- **Candidate work:** validate spawn handoff, server/player snapshot authority,
  saved position loading, safe spawn search, and chunk availability before
  finalizing player placement.

### MP-B002: Second Player World Streaming Is Incomplete And Jittery

- **Status:** open
- **Observed:** second player may only see a small area of chunks, can stutter,
  and can appear to run through air while chunks are missing.
- **Desired:** multiplayer clients stream enough chunks around their own camera
  position, wait for nearby collision/render chunks when needed, and interpolate
  remote players smoothly.
- **Candidate work:** audit client chunk subscription radius, networked chunk
  delivery priority, local physics against unloaded chunks, and remote player
  interpolation/fallback rendering.

## World Feel And Generation

### WORLD-B001: Minecraft-Like World Creation Presets

- **Status:** open
- **Observed:** generation settings exist, but the player-facing new-world flow
  does not yet communicate strong Minecraft-like choices such as world type,
  world shape, size, theme, seed, and feature density.
- **Desired:** new-world creation should offer simple presets that produce
  noticeably different readable worlds: inland/default, island, floating,
  flat/debug, twilight woods, highlands, swamp, and cave-heavy variants.
- **Architecture direction:** presets should be domain/application data, not UI
  conditionals. UI selects a `WorldPresetId`; application resolves it into a
  deterministic `WorldGenerationConfig`; engine/generation consumes the config.
- **Candidate data shape:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class WorldPreset:
    id: str
    label: str
    terrain_profile: str
    biome_profile: str
    feature_profile: str
    default_render_distance: int

@dataclass(frozen=True)
class WorldGenerationConfig:
    seed: int
    terrain_profile: str
    biome_profile: str
    feature_profile: str
    world_shape: str
    world_size_hint: str
```

- **Acceptance idea:** two worlds with the same preset and seed produce identical
  chunk/feature snapshots without Pyglet/OpenGL; different presets are visibly
  distinct in a screenshot/manual smoke scene.

### WORLD-B002: Distant Landmarks And Biome Silhouettes

- **Status:** open
- **Observed:** deterministic highland/plain/swamp silhouettes plus ruin, camp,
  and spire density coverage exist, but a fresh spawn still does not guarantee
  a readable nearby horizon landmark or cave-mouth hint.
- **Desired:** from spawn, the player should usually see at least one readable
  horizon feature: hill ridge, forest edge, swamp basin, tower/pillar, cave
  mouth, or generated structure hint.
- **Architecture direction:** keep base terrain deterministic and testable in
  `engine/generation`; add a feature-placement pass that emits lightweight
  placement records before block mutation. Rendering should only visualize final
  chunks or debug overlays, not decide placement.
- **Candidate work:** measure landmark visibility from actual safe-spawn camera
  positions, then add only the missing spawn-aware spacing/selection or
  cave-mouth decoration needed by a deterministic visual acceptance scene.

### WORLD-B003: Minecraft-Like Block Interaction Event Spine

- **Status:** open
- **Observed:** typed interaction-start/broken/placed events already synchronize
  hand swing and block audio, but particles, item durability, use actions, and
  multiplayer authority still lack the same complete event chain.
- **Desired:** mining/placing/using blocks should feel like one physical event
  chain: input starts intent, simulation validates it, gameplay event is emitted,
  presentation plays swing/particles/sound, network sends compact authority
  state.
- **Architecture direction:** engine/application emits typed events; render,
  audio, network adapters subscribe through ports. Do not let render call
  gameplay mutation directly.
- **Candidate work:** extend the existing events with actor/tool/drop authority
  data, particle intent, durability mutation, use actions, and compact network
  replication without reimplementing the already-routed swing/audio path.
- **Acceptance idea:** unit tests prove durability, particles, and replication
  derive from the validated interaction event without constructing `GameWindow`.

## Rendering And Resource Packs

### R-B002: Minecraft Resource-Pack Grass/Foliage Looks Distorted

- **Status:** open
- **Observed:** applying Minecraft-like resource packs can still make some
  grass/foliage assets render as distorted curtains or oversized cutout sheets.
- **Desired:** Minecraft Java-style grass/foliage textures map to equivalent
  model semantics: grass-block top/side/overlay, crossed-plane plant blocks,
  cutout leaves, biome tint, and resource-location aliases.
- **Architecture direction:** keep texture-pack importing resource-location
  native. Avoid mapping-first shortcuts; map pack assets into a render-material
  model that chunk meshing can consume.
- **Candidate work:** verify imported packs visually, add missing aliases/tint
  metadata or sampling fixes only for a captured concrete failure, and add that
  pack-specific fixture before changing general atlas/model behavior.

### R-B004: Grass Block Surface Tiling Still Looks Too Noisy

- **Status:** open
- **Observed:** grass-block surfaces read as repeated noisy pixels instead of
  continuous Minecraft-like green ground cover, especially with detailed resource
  packs at shallow camera angles.
- **Desired:** terrain keeps source texture resolution, but large grass fields
  read as coherent surfaces without visible atlas seams, random tile flips, or
  harsh per-block discontinuity.
- **Candidate work:** add grass material visual pass with atlas gutters,
  mip-safe sampling, optional distance-biased texture filtering, biome color
  smoothing, and/or subtle terrain overlay blending that does not blur
  inventory/held-item textures.

## Performance

### PERF-B001: Render Distance Above Two Chunks Too Slow

- **Status:** open
- **Observed:** increasing render distance beyond two chunks can make gameplay
  lag heavily even on an M4 machine with 24 GB RAM, while Minecraft sustains
  higher FPS at much larger render distances. Distance, visibility, and
  collision-critical queue priority are now bounded. N9 measured update-bound
  frames in `238/240` RD3 samples and `240/240` RD4 samples. N10 attributed the
  dominant update cost to `relight_chunks`/`_propagate_light`; N11 reduced its
  scratch churn while preserving exact output. The all-zero source fast path has
  moved into the active N12 workplan.
- **Desired:** chunk generation, meshing, uploading, and streaming are bounded
  and prioritized enough for smooth play at higher render distances.
- **Candidate work:** after N12, reprofile the same RD4 workload and select the
  next remaining measured hotspot. Tune worker counts or evaluate process/thread
  splits only if later attribution shows those choices are relevant.

### PERF-B002: Frame Budget And Chunk Pipeline Instrumentation

- **Status:** open
- **Observed:** `RuntimePerfSnapshot` already reports update/render/frame timing
  and all current bounded streaming queue depths. A coarse update-vs-render
  bottleneck label has moved into the active N8 workplan; the remaining backlog
  scope does not yet separate generation, GPU upload, dirty work, or a
  fine-grained slowest subsystem.
- **Desired:** each frame exposes a compact budget summary: simulation time,
  render time, chunk generation jobs, mesh jobs, upload jobs, queue depth,
  visible chunks, dirty chunks, and slowest subsystem.
- **Architecture direction:** collect timings in a small application-facing
  diagnostics service updated at bounded frequency. Render HUD reads a snapshot;
  it should not time subsystems by reaching into internals.
- **Candidate work:** after N8, extend the existing snapshot rather than
  replacing it, sample missing stage timings at bounded frequency, and add
  generation/upload/dirty detail only where a real benchmark can populate it;
  then refine the coarse label from measured evidence.

### PERF-B004: Hot-Path Native/Cython Acceleration Spike

- **Status:** open
- **Observed:** pure Python remains valuable for testability, but meshing,
  lighting propagation, block scans, collision queries, and terrain noise can
  become hot paths as render distance grows.
- **Desired:** accelerate only measured hot loops while keeping gameplay rules
  testable and architecture boundaries intact.
- **Architecture direction:** profile first. If needed, add optional native
  helpers under an engine-owned performance package. Public APIs stay Python
  dataclasses/protocols; extension modules should accept primitive arrays and
  return plain mesh/light buffers. Do not let Cython import `render/window.py`,
  Pyglet, ModernGL, settings, or UI.
- **Candidate Cython sketch:**

```cython
# src/voxel_sandbox/engine/perf/cy_mesh.pyx
# cython: boundscheck=False, wraparound=False, cdivision=True

cpdef int count_visible_faces(
    const unsigned short[:, :, :] block_ids,
    const unsigned char[:] opaque_by_id,
) except -1:
    cdef Py_ssize_t x, y, z
    cdef int faces = 0
    cdef unsigned short block_id

    for y in range(block_ids.shape[0]):
        for z in range(block_ids.shape[1]):
            for x in range(block_ids.shape[2]):
                block_id = block_ids[y, z, x]
                if block_id == 0:
                    continue
                # Real implementation would bounds-check neighbors and add
                # only faces adjacent to air/cutout/non-opaque blocks.
                faces += 6
    return faces
```

- **Candidate Python wrapper:**

```python
try:
    from voxel_sandbox.engine.perf.cy_mesh import count_visible_faces
except ImportError:
    from voxel_sandbox.engine.perf.py_mesh import count_visible_faces
```

- **Acceptance idea:** the Python fallback and Cython path must pass the same
  deterministic fixtures and produce byte-for-byte equivalent mesh summaries.
  Packaging must tolerate missing compiled extensions in development.

### PERF-B005: Mesh Data Layout And GPU Upload Budget

- **Status:** open
- **Observed:** even fast meshing can stutter if upload-ready data is too large,
  fragmented, or pushed to GPU without budget.
- **Desired:** chunk mesh output is compact, cache-friendly, and uploaded in
  bounded batches; large texture-pack atlases do not force unnecessary remeshes.
- **Candidate work:** evaluate struct-of-arrays vs interleaved vertex buffers,
  compact block/material ids, dirty-region remeshing, upload ring/batch budget,
  atlas versioning, and avoiding remesh when only sampler/filter settings change.

### PERF-B006: Lighting And Fluid Update Budgets

- **Status:** open
- **Observed:** lighting and water/fluid updates can become invisible frame-time
  spikes when many blocks change or chunks load together.
- **Desired:** light/fluid propagation advances in deterministic bounded work
  units with visible progress and no long render-thread stalls.
- **Architecture direction:** keep simulation correctness in engine tests; expose
  dirty work counts through diagnostics; render consumes resulting snapshots.
- **Candidate work:** queue-based propagation budgets, chunk-local dirty masks,
  cross-chunk neighbor invalidation tests, and stress scenes for breaking blocks
  near water/light sources.

### PERF-B007: Prove The Low-End 60 FPS Baseline

- **Status:** open
- **Observed:** the `low_60` quality profile and frame-streaming benchmark exist,
  but no recorded two-core/720p acceptance run proves p95 frame time and queue
  stability on the intended low-end target.
- **Desired:** a `low_60` profile targets stable 60 FPS at 720p on a two-core
  CPU-class machine before high-end visual effects are enabled. The profile can
  look simpler, but it must remain readable, Minecraft-like, and free of chunk
  upload stutter during normal walking.
- **Architecture direction:** measure first. Keep frame timing and queue
  counters outside render hot paths, then tune worker counts, upload budgets,
  render distance, and shader variants through `RenderQualityProfile`.
- **Candidate work:** add benchmark/manual smoke route for a deterministic
  walking camera path; record p50/p95/p99 frame time, mesh/generation/upload
  queue depths, visible sections, and enabled effects; compare `low_60`,
  `balanced`, and `high` presets.
- **Acceptance idea:** benchmark output proves p95 frame time stays below
  16.7 ms on the target low profile in a controlled scene, or documents the
  measured blocker subsystem before any expensive visual feature is promoted.
