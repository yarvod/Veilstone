# Next steps

Phase 08 is ready for manual testing. Do not begin Phase 09 until this milestone is accepted.

1. Run `uv run python -m voxel_sandbox`.
2. Switch `F9` between greedy and visible-face meshing while watching `Triangles`.
3. Inspect terrain and trees for texture stretching, dark borders, crosses, or missing faces.
4. Toggle `F6` smooth lighting and `F7` AO in both mesh modes.
5. Place a Gloam Lantern near ordinary terrain and verify relighting/remeshing.
6. Run `uv run python -m voxel_sandbox benchmark-mesher` and `benchmark-lighting`.
7. After acceptance, begin Phase 09 water and the transparent render pass.
