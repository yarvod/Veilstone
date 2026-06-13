from __future__ import annotations

import pytest

from voxel_sandbox.__main__ import main

pytestmark = pytest.mark.smoke


def test_primary_player_entry_starts_and_stops() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    assert main(["--smoke-test"]) == 0


def test_dedicated_server_starts_and_stops() -> None:
    assert main(["server", "--smoke-test"]) == 0
