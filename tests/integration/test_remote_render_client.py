from __future__ import annotations

import tempfile
import time
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
