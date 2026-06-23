# Veilstone Backlog

This backlog captures observed product gaps that should feed future active
`docs/WORKPLAN.md` phases. Keep `WORKPLAN` focused on work currently being
implemented; move backlog items into the workplan when a slice becomes active.

## Multiplayer

### MP-B001: Second player can spawn underground or far from expected origin

- **Status:** open
- **Observed:** in multiplayer, a joining/second player can load underground or
  far away from the intended spawn/origin area.
- **Desired:** joining players spawn at a safe, deterministic, server-authoritative
  location near the world spawn unless a valid saved player position exists.
- **Candidate work:** validate spawn handoff, server/player snapshot authority,
  saved position loading, safe spawn search, and chunk availability before
  finalizing player placement.

### MP-B002: Second player world streaming is incomplete and jittery

- **Status:** open
- **Observed:** a second player may only see a small area of a few chunks, can
  stutter, and can appear to run through air while chunks are missing.
- **Desired:** multiplayer clients stream enough chunks around their own camera
  position, wait for nearby collision/render chunks before active movement when
  necessary, and interpolate remote players smoothly.
- **Candidate work:** audit client chunk subscription radius, networked chunk
  delivery priority, local physics against unloaded chunks, and remote player
  interpolation/fallback rendering.

## Rendering And Resource Packs

### R-B001: Default short grass renders like green reinforcement cubes

- **Status:** open
- **Observed:** default resource-pack grass/short grass can appear as green cage
  or crossed structural planes inside block-sized cubes instead of Minecraft-like
  small grass tufts.
- **Desired:** default grass uses a Minecraft-like cross/plant model with correct
  cutout texture, tint, scale, placement, and no misleading full-cube silhouette.
- **Candidate work:** verify plant block model data, procedural fallback texture,
  atlas alpha/cutout handling, block outline rules, and resource-pack mapping for
  `minecraft:block/short_grass` / `grass`.

### R-B002: Minecraft resource-pack grass/foliage still looks distorted

- **Status:** open
- **Observed:** applying a Minecraft-like resource pack can make grass/foliage
  render as distorted curtains or oversized cutout sheets.
- **Desired:** Minecraft Java-style grass/foliage textures map to the same model
  semantics as Minecraft: grass block top/side overlay for blocks, and small
  crossed planes for plant blocks.
- **Candidate work:** separate block textures from plant textures, verify
  resource-pack aliases, and add visual smoke scenes for default and imported
  grass.

## Diagnostics

### DX-B001: F3 overlay lacks Minecraft-like diagnostics

- **Status:** open
- **Observed:** F3 does not yet show enough practical debugging information such
  as FPS, precise coordinates, chunk/block coordinates, memory, biome, facing,
  render distance, chunk/mesh counts, and runtime/device details.
- **Desired:** F3 is useful for diagnosing world streaming, performance, spawn,
  biome, and rendering issues without adding expensive per-frame telemetry.
- **Candidate work:** extend cached HUD debug data and integration tests.

## Performance

### PERF-B001: Render distance above two chunks is too slow

- **Status:** open
- **Observed:** increasing render distance beyond two chunks can make gameplay
  lag heavily even on an M4 machine with 24 GB RAM, while Minecraft can sustain
  high FPS at much larger render distances.
- **Desired:** chunk generation, meshing, uploading, and streaming are bounded,
  prioritized, and parallelized enough for smooth play at higher render
  distances.
- **Candidate work:** profile generation/meshing/upload budgets, add frame-time
  instrumentation, prioritize visible/near chunks, avoid blocking renderer paths,
  tune worker counts, and evaluate process/thread split for generation and
  meshing.
