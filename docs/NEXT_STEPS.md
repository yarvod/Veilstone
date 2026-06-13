# Next steps

Phase 11 is ready for manual testing. Development continues with Phase 12 after this gate.

1. Run `uv run python -m voxel_sandbox`.
2. Find the blue-gray passive mobs and confirm they wander without chasing the player.
3. Approach a crimson hostile mob and verify it chases, attacks, and reduces `Health`.
4. Aim at a mob and left-click repeatedly; verify death creates a small gold item entity.
5. Walk over the item entity and verify it enters inventory and disappears from the world.
6. Press `Q` and confirm the selected item appears as a rotating/bobbing entity.
7. Move far from mobs and verify population despawns/replenishes around the player.
8. Run `uv run python -m voxel_sandbox benchmark-frame-streaming`.
