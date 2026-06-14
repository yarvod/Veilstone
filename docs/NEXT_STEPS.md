# Next steps

Phase 14 multiplayer polish is in progress.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Run `uv run python -m voxel_sandbox`.
2. Add sequence IDs and delta entity snapshots with periodic full baselines.
3. Add disconnect state, bounded reconnect attempts, and clean return to Multiplayer menu.
4. Connect Direct Connect and discovered LAN worlds to the existing `ClientSession` path.
5. Add nickname and chat text input UI.
6. Make Open to LAN expose the current in-process singleplayer authority, not a second world.
7. Add an 8-client/200-entity server benchmark and enforce the 20 TPS budget.
8. Run `uv run pytest -q tests/integration/test_lan_client_server.py`.
9. Run `uv run python -m voxel_sandbox benchmark-network`.
