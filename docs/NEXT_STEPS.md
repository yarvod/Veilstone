# Next steps

Phase 14 multiplayer polish is complete. Phase 15 shadow and shader polish is next.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Add configurable shadow quality and an explicit off/low/medium setting.
2. Add a depth texture and framebuffer owned by the world renderer.
3. Compute a stable directional sun view-projection matrix around the camera.
4. Add a depth-only chunk shader and shadow render pass.
5. Sample the shadow map in the opaque chunk shader with tunable bias.
6. Add 3x3 PCF filtering for medium quality.
7. Extend the depth pass to articulated entity geometry.
8. Add a GPU/frame benchmark for the target shadow scene.
9. Add sun, moon, and sky geometry after the shadow path is stable.
10. Run the full quality gate and manual visual comparison on low/medium/off.
