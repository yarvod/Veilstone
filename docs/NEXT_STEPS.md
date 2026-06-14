# Next steps

Phase 14 multiplayer polish is in progress.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Run `uv run python -m voxel_sandbox`.
2. Add visible disconnect state and clean return to the Multiplayer menu after retry exhaustion.
3. Add reusable text-entry UI for Direct Connect address, nickname, and chat.
4. Make Open to LAN expose the current in-process singleplayer authority, not a second world.
5. Add an 8-client/200-entity server benchmark and enforce the 20 TPS budget.
8. Run `uv run pytest -q tests/integration/test_lan_client_server.py`.
9. Run `uv run python -m voxel_sandbox benchmark-network`.
