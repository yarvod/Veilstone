# Next steps

Phase 13 local multiplayer MVP is ready for manual two-process testing.

Mob visual note: current colored cuboids are Phase 11 gameplay proxies. Original textured,
articulated mobs with independently animated body parts are an explicit Phase 20 gate.

1. Run `uv run python -m voxel_sandbox`.
2. In terminal one run `uv run python -m voxel_sandbox server --port 25565`.
3. In terminal two run `uv run python -m voxel_sandbox client --connect 127.0.0.1:25565`.
4. Start a second client and verify remote player proxies and block replication.
5. Phase 14: add interpolation/reconciliation and chunk/entity interest management.
6. Phase 14: connect Direct Connect and LAN discovery menus to the working client path.
7. Phase 14: add nickname input, chat UI, reconnect, and rate limiting.
8. Run `uv run pytest -q tests/integration/test_lan_client_server.py`.
9. Run `uv run python -m voxel_sandbox benchmark-network`.
