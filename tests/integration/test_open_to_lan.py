from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.app.settings import AppSettings, WorldSettings
from voxel_sandbox.network import LanClient, Message
from voxel_sandbox.network.discovery import discover_worlds

pytestmark = pytest.mark.smoke


def _receive_type(client: LanClient, expected: str) -> Message:
    for _ in range(8):
        message = client.receive()
        if message.get("type") == expected:
            return message
    raise AssertionError(f"Did not receive {expected}")


def test_open_to_lan_exposes_active_world_and_applies_remote_edits(tmp_path: Path) -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    settings = AppSettings(
        world=WorldSettings(generation_backend="thread", meshing_backend="thread")
    )
    window = GameWindow(settings, visible=False, save_root=tmp_path)
    client = LanClient()
    try:
        window.open_to_lan()
        assert window.lan_server is not None
        worlds = discover_worlds(port=25565, timeout=0.2, target="127.0.0.1")
        assert any(world.port == window.lan_server.address[1] for world in worlds)

        client.connect(*window.lan_server.address, name="LAN Guest")
        client.send({"type": "input", "position": [8.5, 40.0, 8.5]})
        _receive_type(client, "entity_snapshot")
        client.send({"type": "block_action", "position": [8, 40, 8], "block_id": 10})
        _receive_type(client, "block_delta")
        window.fixed_update(1.0 / 60.0)

        assert window.world_renderer.get_block(8, 40, 8) == 10
    finally:
        client.close()
        window.close()
