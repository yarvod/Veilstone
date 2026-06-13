# ADR 0002: Voxel lighting and shadow strategy

## Status

Accepted.

## Decision

Sky and emissive block light are stored as 4-bit-equivalent voxel levels (`0..15`). A
bounded NumPy flood propagation updates those arrays only when chunks load or blocks change.
Meshing samples a two-voxel halo from loaded neighboring sections and bakes sky light, block
light, and ambient occlusion into mesh vertices.

Ambient occlusion is a local contact-darkening approximation based on the three neighboring
voxels around each vertex. It is not a cast shadow. Greedy meshing only combines faces with
compatible material, light, and AO signatures.

Sun shadows in Phase 15 will use a GPU depth shadow map for nearby visible casters, followed
by shadow-map lookup and PCF filtering in the world shader. Optional cascades may extend the
distance if the measured GPU frame budget allows it.

## Rejected alternatives

- CPU rays from every light to blocks or fragments: work scales poorly with lights and world
  size and cannot satisfy the frame budget.
- Full-world lighting every frame: most light data is unchanged and must remain event-driven.
- Per-block draw calls: incompatible with chunk batching and the GPU frame budget.

## Performance constraints

- Visible-face meshing: at most `2 ms` per `16^3` section on the reference machine.
- Greedy meshing: at most `4 ms` per `16^3` section.
- Medium GPU frame target: at most `12 ms`, including the future shadow depth pass.
