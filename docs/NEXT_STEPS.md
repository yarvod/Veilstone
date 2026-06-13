# Next steps

Phase 12 is ready for manual testing. Development continues with Phase 13 after this gate.

1. Run `uv run python -m voxel_sandbox`.
2. Break/place a distinctive block, change inventory/hotbar selection, and move elsewhere.
3. Exit normally, rerun the game, choose Load World, and verify block/player/inventory state.
4. Move far enough to unload an edited chunk, return, and verify the edit remains.
5. Inspect `saves/dev_world/level.toml`, `players/`, and compressed files under `regions/`.
6. Leave the game running beyond five seconds and verify autosave timestamps/files update.
7. Run `uv run pytest -q tests/integration/test_world_persistence.py`.
8. Run `uv run python -m voxel_sandbox benchmark-frame-streaming`.
