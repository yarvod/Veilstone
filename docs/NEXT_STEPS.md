# Next steps

Phase 10 is ready for manual testing. Development continues with Phase 11 after this gate.

1. Run `uv run python -m voxel_sandbox`.
2. Use `1-4` and the mouse wheel to switch hotbar slots; place blocks with right click.
3. Break a log, approach the drop until `Drops` decreases, and inspect the collected stack.
4. Press `E`; test left-click move/swap, right-click split/place-one, and Shift-click quick move.
5. Press `C` with a collected log to craft planks, then craft and place a Runecraft Table.
6. Right-click the table to open 3x3 crafting and craft a Gloam Lantern when materials exist.
7. Press `Q` to drop one selected item and walk over it to collect it again.
8. Run `uv run python -m voxel_sandbox benchmark-frame-streaming`.
