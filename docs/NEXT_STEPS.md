# Next steps

Phase 09 is ready for manual testing. Development continues with Phase 10 after this gate.

1. Run `uv run python -m voxel_sandbox`.
2. Find a generated lake and inspect transparency, animated surface movement, and shore faces.
3. Press `3`, place water over a ledge, and verify it falls before spreading sideways.
4. Enter water and verify the short blue underwater fog range.
5. Switch `F9` and confirm water remains separate in both opaque mesh modes.
6. Watch frame time while crossing chunk boundaries near water.
7. Run `uv run python -m voxel_sandbox benchmark-frame-streaming`.
