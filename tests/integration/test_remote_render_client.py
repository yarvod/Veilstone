from __future__ import annotations

import tempfile
import time
from dataclasses import replace
from pathlib import Path

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.network import LanServer

pytestmark = pytest.mark.smoke


def test_graphical_client_installs_server_chunk() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    server = LanServer("127.0.0.1", 0, seed="remote-render")
    server.start()
    with tempfile.TemporaryDirectory(prefix="veilstone-remote-test-") as directory:
        window = GameWindow(
            AppSettings(),
            visible=False,
            save_root=Path(directory),
            connect=f"{server.address[0]}:{server.address[1]}",
        )
        try:
            deadline = time.monotonic() + 3.0
            while window.remote_chunks_received == 0 and time.monotonic() < deadline:
                window.fixed_update(1.0 / 60.0)
                time.sleep(0.01)
            window.switch_to()
            window.dispatch_event("on_draw")
            window.flip()

            assert window.remote_chunks_received == 1
        finally:
            window.close()
            server.stop()


def test_two_graphical_clients_create_remote_player_avatars() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    settings = AppSettings()
    settings = replace(
        settings,
        world=replace(settings.world, generation_backend="thread", meshing_backend="thread"),
    )
    with (
        tempfile.TemporaryDirectory(prefix="veilstone-host-avatar-") as host_directory,
        tempfile.TemporaryDirectory(prefix="veilstone-guest-avatar-") as guest_directory,
    ):
        host = GameWindow(
            settings,
            visible=False,
            save_root=Path(host_directory),
            player_name="Host",
        )
        assert host.lan_server is not None
        host.menu.screen = Screen.GAME
        guest = GameWindow(
            settings,
            visible=False,
            save_root=Path(guest_directory),
            connect=f"127.0.0.1:{host.lan_server.address[1]}",
            player_name="Guest",
        )
        try:
            deadline = time.monotonic() + 3.0
            while (
                not host.remote_player_entities or not guest.remote_player_entities
            ) and time.monotonic() < deadline:
                host.fixed_update(0.05)
                guest.fixed_update(0.05)
                time.sleep(0.01)

            assert len(host.remote_player_entities) == 1
            assert len(guest.remote_player_entities) == 1
            for window in (host, guest):
                entity = next(iter(window.remote_player_entities.values()))
                assert window.entities.world.render_models[entity].key == "remote_player"
                assert window.entities.world.transforms.get(entity) is not None
        finally:
            guest.close()
            host.close()
