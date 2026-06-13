# Next steps

Phase 07 is ready for manual testing. Do not begin Phase 08 until this milestone is accepted.

1. Run `uv run python -m voxel_sandbox`.
2. Test `F6` smooth lighting, `F7` ambient occlusion, and `F8` fog.
3. Select the Gloam Lantern with `2`, then place and remove it in a dark recess.
4. Observe the day/night tint or temporarily set `day_cycle_seconds = 30.0`.
5. Run `uv run python -m voxel_sandbox benchmark-lighting`.
6. Record lighting seams or visual artifacts.
7. After acceptance, begin Phase 08 greedy meshing.
