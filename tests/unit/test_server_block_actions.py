from __future__ import annotations

from voxel_sandbox.network.server import ServerState


def test_server_rejects_player_water_removal() -> None:
    state = ServerState("water-protection")
    position = (8, 40, 8)
    state.apply_block_action(position, 8, notify_sink=False)

    assert not state.allows_player_block_action(position, 0)
    assert state.allows_player_block_action(position, 1)


def test_server_rejects_unknown_block_id() -> None:
    state = ServerState("block-validation")

    assert not state.allows_player_block_action((0, 40, 0), 9999)
