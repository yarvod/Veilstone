from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.app.settings import AppSettings, WorldSettings

pytestmark = pytest.mark.smoke


def test_create_and_load_world_keep_separate_player_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    monkeypatch.chdir(tmp_path)
    settings = AppSettings(
        world=WorldSettings(generation_backend="thread", meshing_backend="thread")
    )
    window = GameWindow(settings, visible=False, save_root=tmp_path / "initial")
    try:
        window.create_world("Alpha Realm", "alpha-seed")
        alpha_root = window.active_save_root
        window.player.x = 12.5
        window.player.z = 9.5

        window.create_world("Beta Realm", "beta-seed")
        assert window.active_save_root != alpha_root
        assert window.world_renderer.seed_text == "beta-seed"

        assert window.load_world("Alpha Realm")
        assert window.active_save_root == alpha_root
        assert window.world_renderer.seed_text == "alpha-seed"
        assert window.player.x == 12.5
        assert window.player.z == 9.5
    finally:
        window.close()
