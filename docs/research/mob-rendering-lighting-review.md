# Mob rendering and voxel lighting review

Comparative references reviewed on 2026-06-15:

- `obiwac/python-minecraft-clone` for semantic face materials and separate collision geometry.
- `fogleman/Craft` for exposed-face chunk meshes, neighbor overlap, normals, and shader-driven
  lighting in a compact voxel engine.
- `luanti-org/luanti` as a mature reference for chunked voxel-world lighting architecture.
- `ClassiCube/ClassiCube` as a mature reference for simple block-model rendering and movement.

No source code, Minecraft textures, model files, or asset layouts were copied. The applicable
principles were implemented independently in the existing Veilstone architecture.

## Decisions

- Mob skins are generated from deterministic orthographic face tiles. Front, side, back, top and
  bottom regions contain content authored for that exact orientation.
- Entity vertices carry face normals. Entity and runtime-structure fragments use world skylight,
  block light, daylight tint, directional light, and the terrain shadow map. Terrain and entity
  diffuse lighting use the same moving celestial direction that builds the shadow matrix.
- Loaded neighboring chunks are relit as one bounded 3x3 region. Missing chunks are treated as a
  closed boundary, while loaded borders participate in the same 15-level flood fill.
- AI direction is a desired heading. Actual horizontal velocity is derived only from current yaw,
  with speed reduced while turning, so articulated mobs do not slide sideways.

## Performance

A synthetic nine-chunk cross-boundary relight measures approximately `8.9 ms` on the development
machine. It is triggered only for loaded neighborhoods affected by loading, unloading, fluid or
block changes; meshing remains asynchronous.
