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
  controllers still receive the full window instead of narrow ports.
- **Desired:** `GameWindow` becomes a thin presentation shell: application
  use-cases own orchestration, snapshots cross render/network/UI boundaries,
  renderer adapters consume render data, and tests cover most behavior without
  constructing Pyglet/ModernGL objects.
- **Candidate work:** split HUD/debug snapshots, input command ports, gameplay
  command use-cases, network presentation adapters, world-runtime lifecycle
  ownership, and renderer settings ports into small independently verified
  slices.
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
- **Observed:** terrain has more biome variety than early MVP, but distant views
  still do not consistently produce memorable Minecraft-like silhouettes or
  navigable landmarks.
- **Desired:** from spawn, the player should usually see at least one readable
  horizon feature: hill ridge, forest edge, swamp basin, tower/pillar, cave
  mouth, or generated structure hint.
- **Architecture direction:** keep base terrain deterministic and testable in
  `engine/generation`; add a feature-placement pass that emits lightweight
  placement records before block mutation. Rendering should only visualize final
  chunks or debug overlays, not decide placement.
- **Candidate work:** add feature budget per region, landmark spacing rules,
  biome-aware height exaggeration, cave-mouth decorators, and debug snapshot
  tests that assert feature density and spacing.

### WORLD-B003: Minecraft-Like Block Interaction Event Spine

- **Status:** open
- **Observed:** player hand swing, block sounds, breaking feedback, particles,
  item durability, and future multiplayer replication are related actions but
  can drift if each subsystem observes input separately.
- **Desired:** mining/placing/using blocks should feel like one physical event
  chain: input starts intent, simulation validates it, gameplay event is emitted,
  presentation plays swing/particles/sound, network sends compact authority
  state.
- **Architecture direction:** engine/application emits typed events; render,
  audio, network adapters subscribe through ports. Do not let render call
  gameplay mutation directly.
- **Candidate event sketch:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BlockInteractionStarted:
    actor_id: int
    block_pos: tuple[int, int, int]
    face: int
    tool_item_id: str | None

@dataclass(frozen=True)
class BlockBroken:
    actor_id: int
    block_pos: tuple[int, int, int]
    block_id: str
    drops: tuple[str, ...]
```

- **Acceptance idea:** unit tests can prove hand animation, sound routing, and
  particle intent derive from the same event without constructing `GameWindow`.

### WORLD-B004: Reference Gameplay Snapshot Scenes

- **Status:** open
- **Observed:** Minecraft-like feel is hard to protect with isolated unit tests
  alone.
- **Desired:** keep a small set of deterministic reference scenes for generation,
  water, foliage, lighting, mob movement, inventory icons, and first-person
  interaction.
- **Candidate work:** add debug scene fixtures plus screenshot/manual smoke
  commands. Store numeric summaries first; visual golden images can follow only
  after render output stabilizes enough to avoid churn.

### WORLD-B005: Swimming Stroke Audio Polish

- **Status:** open
- **Observed:** water enter/exit splash events exist, but continuous swimming still lacks a distinct stroke/loop feel and dedicated splash assets.
- **Desired:** swimming should have a soft Minecraft-like loop/stroke cadence separate from landing or water-entry splashes, routed through gameplay/audio events rather than render-window state.
- **Architecture direction:** player movement or application presentation emits swim cadence events; audio adapter resolves resource-pack sound locations under `resource_packs/default/assets/<namespace>/sounds/...`.
- **Candidate work:** add swim cadence state, default resource-pack stroke/splash sounds, event-to-audio routing tests, and a real water movement smoke check.

## Rendering And Resource Packs

### R-B001: Default Short Grass Renders Like Green Reinforcement Cubes

- **Status:** fixed
- **Observed:** default resource-pack grass/short grass could appear as green
  cage or crossed structural planes inside block-sized cubes instead of
  Minecraft-like small grass tufts.
- **Desired:** default grass uses Minecraft-like cross/plant model semantics,
  correct cutout texture, tint, scale, placement, and no misleading full-cube
  silhouette.
- **Fix notes:** `short_grass` and `wildflower` now use data-driven
  `render_shape = "cross"` plant mesh instead of full cube faces. Procedural
  short-grass fallback uses sparse bottom-rooted cutout blades without opaque
  texture borders, plant quads receive top-biased lighting, and chunk texture
  variation no longer vertically flips rooted plant textures.

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
  metadata, add atlas gutter/mipmap-safe sampling checks, and add pack-specific
  fixtures for concrete failures.

### R-B003: Cutout Plant Shadows Too Faint On Terrain

- **Status:** fixed
- **Observed:** visible plant rendering discarded transparent texels, but thin
  cutout caster shadows could disappear after receiver bias and 3x3 PCF
  filtering, so grass appeared to cast no terrain shadow.
- **Desired:** grass/foliage shadows respect alpha cutouts and remain readable
  enough on nearby terrain without turning transparent texture planes into
  solid-sheet shadows.
- **Fix notes:** chunk shadow-depth rendering receives atlas UV/rect attributes,
  binds block atlas, discards transparent texels before writing depth, and the
  receiver shader preserves center shadow hits so thin plant samples are not
  blurred away.

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

### R-B005: Vegetation Wind Animation

- **Status:** open
- **Observed:** grass, leaves, and future plants are static.
- **Desired:** grass/leaves/vegetation use subtle Minecraft-like visual-only
  wind sway while preserving blocky silhouettes, resource-pack textures, and
  deterministic collision/gameplay state.
- **Architecture direction:** animation belongs in render vertex data/shader
  inputs. Simulation should not mutate plant blocks for wind.
- **Candidate work:** drive visual-only vertex shader sway from world time,
  biome/wind settings, block/material kind, and chunk coordinates; add
  screenshot/manual smoke scenes for animated vegetation.

### R-B006: Block/Item Model Snapshot Layer

- **Status:** open
- **Observed:** inventory, held items, player hand, dropped items, and chunk
  blocks can drift visually because each path can interpret item/block rendering
  differently.
- **Desired:** a block/item has one render-facing model description that can be
  reused by chunk meshing, held item rendering, inventory icons, drops, and
  remote-player held items.
- **Architecture direction:** domain owns item/block identity and gameplay
  metadata; application/render adapter builds `RenderModelSnapshot`; render
  consumes the snapshot. UI must not mutate domain inventory internals to obtain
  visuals.
- **Candidate shape:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RenderModelSnapshot:
    resource_id: str
    model_kind: str
    texture_slots: dict[str, str]
    tint: tuple[float, float, float] | None
    cutout: bool
    icon_camera: str
```

### R-B007: Iris/PBR-Like Shader Material Pipeline

- **Status:** open
- **Observed:** Veilstone supports Minecraft Java-style color textures, cutout
  alpha, fog, smooth lighting, AO, water animation, and shadow maps, but not
  shaderpack-style material inputs such as normal/specular/emissive/parallax
  maps. PBR resource packs therefore import mostly as flat color atlases.
- **Desired:** high-quality mode can make resource packs read closer to
  Iris/shaderpack screenshots: directional light, soft-ish block shadows,
  emissive blocks, richer water/sky response, normal/specular material detail,
  and optional screen-space reflections where hardware allows it.
- **Architecture direction:** keep shader/material metadata in render-facing
  snapshots and atlas build outputs. Domain registries should name block/item
  identity and gameplay data only. Renderer owns quality tiers and extra GPU
  textures; application/settings select tiers.
- **Candidate work:** continue from material metadata, parallel material atlases,
  `MaterialVisualSnapshot`, material visual lookup consumers, shader variant
  selection, material atlas binding plans, shader setup/runtime fixtures,
  `WorldScene` planning hook, runtime wiring plans, and material-preview shader
  fixtures into opt-in `WorldScene` activation and shader use; add emissive
  conventions/LabPBR-style metadata, and keep low-tier chunks color-only.
- **Acceptance idea:** a deterministic PBR fixture pack produces color, normal,
  and material atlases with matching UV rects; low-tier renders the same chunks
  without binding those atlases; high-tier screenshot/manual smoke scene shows
  visible normal/specular/emissive differences.

### R-B008: Scalable Visual Quality Tiers

- **Status:** open
- **Observed:** realistic graphics and weak-machine 60 FPS pull in opposite
  directions if every effect is always on.
- **Desired:** settings expose clear presets such as `low_60`, `balanced`,
  `high`, and `cinematic`, each mapping to concrete render behavior: render
  distance, shadows, AO, water quality, clouds, vegetation wind, PBR maps,
  reflections, and postprocess.
- **Architecture direction:** use a small render-quality policy object consumed
  by renderer construction and live settings updates. Avoid scattering
  independent booleans across `GameWindow` and `DemoWorldRenderer`.
- **Candidate work:** add preset data under settings, convert current graphics
  flags into resolved `RenderQualityProfile`, and keep F3 showing active preset
  plus expensive enabled effects.
- **Acceptance idea:** changing presets in Settings updates active runtime
  without world reload; low preset disables high-cost shader paths and keeps
  visual fallback correct.

## Diagnostics

### DX-B001: F3 Overlay Lacks Minecraft-Like Diagnostics

- **Status:** open
- **Observed:** F3 does not yet show enough practical debugging information such
  as FPS, precise coordinates, chunk/block coordinates, memory, biome, facing,
  render distance, chunk/mesh counts, runtime/device details, and streaming
  queue depth.
- **Desired:** F3 should diagnose world streaming, performance, spawn, biome,
  rendering, and multiplayer issues without expensive per-frame telemetry.
- **Candidate work:** extend cached HUD debug data with low-frequency sampling
  and integration tests.

### DX-B002: Isometric/Reference Screenshot Tool

- **Status:** open
- **Observed:** manual screenshots exist, but there is no stable debug tool for
  comparing generation, lighting, foliage, and resource-pack output across
  changes.
- **Desired:** a dev-only screenshot command/mode can capture a deterministic
  world region from a known camera preset, including an isometric/debug view.
- **Candidate work:** add screenshot command behind dev/debug UI, seedable scene
  fixture selection, and metadata sidecar with seed, preset, render distance,
  resource pack, commit, and settings.

## Performance

### PERF-B001: Render Distance Above Two Chunks Too Slow

- **Status:** open
- **Observed:** increasing render distance beyond two chunks can make gameplay
  lag heavily even on an M4 machine with 24 GB RAM, while Minecraft sustains
  higher FPS at much larger render distances.
- **Desired:** chunk generation, meshing, uploading, and streaming are bounded
  and prioritized enough for smooth play at higher render distances.
- **Candidate work:** profile generation/meshing/upload budgets, add frame-time
  instrumentation, prioritize visible/near chunks, avoid blocking render paths,
  tune worker counts, and evaluate process/thread split for generation/meshing.

### PERF-B002: Frame Budget And Chunk Pipeline Instrumentation

- **Status:** open
- **Observed:** performance complaints can be hard to classify: generation,
  meshing, GPU upload, texture loading, lighting, entity simulation, and debug
  telemetry can all appear as "lag".
- **Desired:** each frame exposes a compact budget summary: simulation time,
  render time, chunk generation jobs, mesh jobs, upload jobs, queue depth,
  visible chunks, dirty chunks, and slowest subsystem.
- **Architecture direction:** collect timings in a small application-facing
  diagnostics service updated at bounded frequency. Render HUD reads a snapshot;
  it should not time subsystems by reaching into internals.
- **Candidate shape:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RuntimePerfSnapshot:
    frame_ms: float
    simulation_ms: float
    render_ms: float
    chunk_generation_queue: int
    mesh_queue: int
    upload_queue: int
    visible_chunks: int
    dirty_chunks: int
```

### PERF-B003: Prioritized Chunk Streaming And Mesh Scheduling

- **Status:** open
- **Observed:** chunk work can block or arrive in an order that does not match
  what the player needs right now.
- **Desired:** player-near, camera-visible, collision-critical chunks win over
  far decorative work; chunk generation, lighting, meshing, and GPU upload each
  have a per-frame budget.
- **Architecture direction:** split world runtime work into stages with explicit
  budgets. `WorldRuntime` owns scheduling policy; `WorldSceneRenderer` only
  uploads/draws ready render data through a narrow port.
- **Candidate shape:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ChunkWorkBudget:
    generation_ms: float
    lighting_ms: float
    meshing_ms: float
    upload_ms: float

class ChunkPipeline:
    def tick(self, camera_chunk: tuple[int, int], budget: ChunkWorkBudget) -> None:
        """Advance bounded chunk work without blocking the render frame."""
        ...
```

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

### PERF-B007: Low-End 60 FPS Baseline

- **Status:** open
- **Observed:** default settings currently favor a nice prototype view: render
  distance 2, process-backed generation and meshing workers, smooth lighting,
  AO, fog, medium shadows, and clouds. On a two-core low-end machine, worker
  processes, simulation, rendering, and OS scheduling can compete for the same
  CPU budget.
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
