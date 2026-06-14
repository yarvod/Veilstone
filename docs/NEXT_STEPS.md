# Next steps

Phase 14 multiplayer polish is complete. Phase 15 shadow and shader polish is next.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Run a visual OpenGL smoke for shadow shader compilation and framebuffer completeness.
2. Tune medium shadow bias against terrain acne and detached shadows.
3. Run `uv run python -m voxel_sandbox benchmark-shadows` with an active display.
4. Verify the medium scene remains within the 12 ms GPU target and tune quality if needed.
5. Polish water reflection tint, fresnel response, and shore depth fade.
6. Add sun, moon, and sky geometry after the shadow path is stable.
7. Add lightweight clouds with a low/off setting.
8. Evaluate optional postprocessing only after the base frame budget passes.
9. Run the full quality gate and manual visual comparison on low/medium/off.
