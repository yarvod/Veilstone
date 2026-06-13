# Next steps

Phase 13 transport is implemented; graphical remote-world integration remains.

1. Run `uv run python -m voxel_sandbox`.
2. Decode received chunk payloads into client-side chunk objects.
3. Add a remote-world source to the existing streamer/renderer boundary.
4. Render server entity snapshots as remote players.
5. Pass `client --connect HOST:PORT` through bootstrap into the graphical client.
6. Connect Direct Connect menu input to the same client path.
7. Route local block actions and chat UI through `LanClient`.
8. Run `uv run pytest -q tests/integration/test_lan_client_server.py`.
9. Run `uv run python -m voxel_sandbox benchmark-network`.
