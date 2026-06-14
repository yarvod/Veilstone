from __future__ import annotations

from voxel_sandbox.network.discovery import DiscoveryResponder, discover_worlds


def test_lan_discovery_finds_world_and_player_count() -> None:
    responder = DiscoveryResponder(
        "127.0.0.1",
        0,
        world_name="Test LAN World",
        game_port=25570,
        player_count=lambda: 3,
    )
    responder.start()
    try:
        worlds = discover_worlds(
            port=responder.address[1],
            timeout=0.2,
            target="127.0.0.1",
        )
    finally:
        responder.stop()

    assert len(worlds) == 1
    assert worlds[0].name == "Test LAN World"
    assert worlds[0].port == 25570
    assert worlds[0].players == 3
