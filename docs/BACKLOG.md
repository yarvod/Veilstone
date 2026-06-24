# Veilstone Backlog

This backlog captures observed product gaps that should feed future active
`docs/WORKPLAN.md` phases. Keep `WORKPLAN` focused on work currently being
implemented; move backlog items into workplan when a slice becomes active.

## Multiplayer

### MP-B001: Second Player Can Spawn Underground Far From Expected Origin

- **Status:** open
- **Observed:** in multiplayer, joining/second player can load underground or
  far away from the intended spawn/origin area.
- **Desired:** joining players spawn at a safe, deterministic,
  server-authoritative location near world spawn unless a valid saved player
  position exists.
- **Candidate work:** validate spawn handoff, server/player snapshot authority,
  saved position loading, safe spawn search, and chunk availability before
  finalizing player placement.

### MP-B002: Second Player World Streaming Is Incomplete And Jittery

- **Status:** open
- **Observed:** second player may only see a small area of a few chunks, can
  stutter, and can appear to run through air while chunks are missing.
- **Desired:** multiplayer clients stream enough chunks around their own camera
  position, wait for nearby collision/render chunks before active movement when
  necessary, and interpolate remote players smoothly.
- **Candidate work:** audit client chunk subscription radius, networked chunk
  delivery priority, local physics against unloaded chunks, and remote player
  interpolation/fallback rendering.

## Rendering Resource Packs

### R-B001: Default Short Grass Renders Like Green Reinforcement Cubes

- **Status:** fixed
- **Observed:** default resource-pack grass/short grass can appear as green cage
  or crossed structural planes inside block-sized cubes instead of
  Minecraft-like small grass tufts.
- **Desired:** default grass uses Minecraft-like cross/plant model with correct
  cutout texture, tint, scale, placement, and no misleading full-cube silhouette.
- **Fix notes:** `short_grass` and `wildflower` now use data-driven
  `render_shape = "cross"` plant mesh instead of full cube faces. Procedural
  short-grass fallback uses sparse bottom-rooted cutout blades without opaque
  texture borders, plant quads receive top-biased lighting, and chunk texture
  variation no longer vertically flips rooted plant textures.

### R-B002: Minecraft Resource-Pack Grass/Foliage Looks Distorted

- **Status:** open
- **Observed:** applying a Minecraft-like resource pack can make grass/foliage
  render as distorted curtains or oversized cutout sheets.
- **Desired:** Minecraft Java-style grass/foliage textures map to the same model
  semantics as Minecraft: grass-block top/side overlay blocks and small
  crossed-plane plant blocks.
- **Fix notes:** plant cutouts keep upright UV orientation because chunk shader
  no longer applies random vertical flips.
- **Candidate work:** verify real imported packs visually, then handle remaining
  texture-pack alias/color/tint issues for concrete imported-pack failures.

### R-B003: Cutout Plant Shadows Too Faint On Terrain

- **Status:** fixed
- **Observed:** visible plant rendering discards transparent texels, but thin
  cutout caster shadows could disappear after receiver bias and 3x3 PCF
  filtering, so grass appeared to cast no terrain shadow.
- **Desired:** grass/foliage shadows respect alpha cutouts and remain readable
  enough on nearby terrain without turning transparent texture planes into
  solid-sheet shadows.
- **Fix notes:** chunk shadow-depth rendering receives atlas UV/rect attributes,
  binds the block atlas, discards transparent texels before writing depth, and
  the receiver shader preserves center shadow hits so thin plant samples are not
  blurred away.

### R-B004: Grass Block Surface Tiling Still Looks Too Noisy

- **Status:** open
- **Observed:** grass-block surfaces read as repeated noisy pixels instead of
  continuous Minecraft-like green ground cover, especially with detailed
  resource packs at shallow camera angles.
- **Desired:** terrain keeps source texture resolution, but large grass fields
  read as coherent surface without visible atlas seams, random tile flips, or
  harsh per-block discontinuity.
- **Candidate work:** add a grass material visual pass with atlas gutters or
  mip-safe sampling, optional distance-biased texture filtering, biome color
  smoothing, and/or subtle terrain overlay blending that does not blur
  inventory/held-item textures.

### R-B005: Vegetation Wind Animation

- **Status:** open
- **Observed:** grass, leaves, and future plants are static.
- **Desired:** grass, leaves, and vegetation use subtle Minecraft-like wind sway
  that preserves blocky silhouettes, respects resource-pack textures, and keeps
  collision/gameplay state deterministic.
- **Candidate work:** drive visual-only vertex shader sway from world time,
  biome/wind settings, and block/material kind; add screenshots/manual smoke
  scenes for still and animated vegetation.

## Diagnostics

### DX-B001: F3 Overlay Lacks Minecraft-Like Diagnostics

- **Status:** open
- **Observed:** F3 does not yet show enough practical debugging information such
  as FPS, precise coordinates, chunk/block coordinates, memory, biome, facing,
  render distance, chunk/mesh counts, and runtime/device details.
- **Desired:** F3 should be useful for diagnosing world streaming, performance,
  spawn, biome, and rendering issues without adding expensive per-frame
  telemetry.
- **Candidate work:** extend cached HUD debug data and integration tests.

## Performance

### PERF-B001: Render Distance Above Two Chunks Too Slow

- **Status:** open
- **Observed:** increasing render distance beyond two chunks can make gameplay
  lag heavily even on an M4 machine with 24 GB RAM, while Minecraft can sustain
  high FPS at much larger render distances.
- **Desired:** chunk generation, meshing, uploading, and streaming are bounded
  and prioritized enough for smooth play at higher render distances.
- **Candidate work:** profile generation/meshing/upload budgets, add frame-time
  instrumentation, prioritize visible/near chunks, avoid blocking renderer
  paths, tune worker counts, and evaluate process/thread split for generation
  and meshing.
